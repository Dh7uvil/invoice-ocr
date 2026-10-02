"""
LLM service for structured invoice parsing using various providers.
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import re
from pathlib import Path

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Pydantic models
from schemas.invoice_models import InvoiceData, InvoiceProcessingResponse

logger = logging.getLogger(__name__)


class BaseLLMService(ABC):
    """Base LLM service interface."""
    
    @abstractmethod
    def parse_invoice(self, text: str, **kwargs) -> InvoiceData:
        """Parse invoice text into structured data."""
        pass

    # Helpers shared by providers
    def _fill_missing_defaults(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure required fields exist with sane defaults to pass validation.
        This does not claim correctness, only schema completeness so downstream
        steps can proceed even when the LLM omits fields.
        """
        data = dict(payload or {})

        def ensure_party(obj: Optional[Dict[str, Any]]) -> Dict[str, Any]:
            party: Dict[str, Any] = dict(obj or {})

            def as_str_required(value: Any) -> str:
                return value if isinstance(value, str) else ""

            # Required strings must be actual strings (empty string if missing/None)
            party["name"] = as_str_required(party.get("name"))
            party["address_line1"] = as_str_required(party.get("address_line1"))

            # Optional fields
            party.setdefault("address_line2", None)
            party.setdefault("postal_code", None)
            party.setdefault("country_code", None)
            party.setdefault("tax_id_no", None)
            party.setdefault("registration_no", None)
            party.setdefault("contact_number", None)
            return party

        def as_int(value: Any) -> int:
            try:
                if value is None or value == "":
                    return 0
                return int(float(value))
            except Exception:
                return 0

        def as_float(value: Any) -> float:
            try:
                if value is None or value == "":
                    return 0.0
                return float(value)
            except Exception:
                return 0.0

        # Root required strings
        for key in ("invoice_file_name", "unique_invoice_number", "invoice_date", "due_date", "invoice_currency_code"):
            if not isinstance(data.get(key), str):
                data[key] = ""

        # Optional root
        if "purchase_order_number" not in data:
            data["purchase_order_number"] = None

        # Parties
        data["supplier_info"] = ensure_party(data.get("supplier_info"))
        data["buyer_info"] = ensure_party(data.get("buyer_info"))
        data["ship_to_info"] = ensure_party(data.get("ship_to_info"))

        # Line items
        items = data.get("line_items")
        if not isinstance(items, list):
            items = []
        sanitized_items: List[Dict[str, Any]] = []
        for item in items:
            it = dict(item or {})
            if not isinstance(it.get("product_description"), str):
                it["product_description"] = ""
            it["classification"] = it.get("classification")
            it["product_number"] = it.get("product_number")
            it["serial_number"] = it.get("serial_number")
            it["quantity_shipped"] = as_int(it.get("quantity_shipped"))
            it["unit_price"] = as_float(it.get("unit_price"))
            it["extended_value"] = as_float(it.get("extended_value"))
            it["tax_rate"] = as_float(it.get("tax_rate"))
            it["tax_value"] = as_float(it.get("tax_value"))
            it["total_value_incl_tax"] = as_float(it.get("total_value_incl_tax"))
            sanitized_items.append(it)
        data["line_items"] = sanitized_items

        # Totals
        data["total_value_excl_tax"] = as_float(data.get("total_value_excl_tax"))
        data["total_tax_value"] = as_float(data.get("total_tax_value"))
        data["total_payable_value"] = as_float(data.get("total_payable_value"))

        return data

    def _heuristic_enrich(self, source_text: str, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lightweight heuristics to fill key fields only if missing/empty.
        Keeps existing values from the model; only fills when falsy.
        """
        data = dict(payload or {})
        text = source_text or ""
        ctx = context or {}

        def first_match(patterns):
            for pat in patterns:
                m = re.search(pat, text, flags=re.IGNORECASE)
                if m:
                    return m.group(1).strip()
            return None

        # File name from context
        if not isinstance(data.get("invoice_file_name"), str) or not data.get("invoice_file_name"):
            fname = ctx.get("file_name")
            if isinstance(fname, str):
                data["invoice_file_name"] = fname

        # Invoice number
        if not isinstance(data.get("unique_invoice_number"), str) or not data.get("unique_invoice_number"):
            inv = first_match([
                r"Invoice\s*(?:No\.?|Number|#)\s*[:]?\s*([A-Za-z0-9\-]+)",
                r"Inv\s*#:?\s*([A-Za-z0-9\-]+)",
                r"\b([A-Z]\d{6,})\b",  # e.g., H121058044
            ])
            if inv:
                data["unique_invoice_number"] = inv

        # Dates
        date_pat = r"(\b\d{1,2}[\-/](?:[A-Za-z]{3}|\d{1,2})[\-/]\d{2,4}\b)"
        if not isinstance(data.get("invoice_date"), str) or not data.get("invoice_date"):
            inv_date = first_match([
                rf"Invoice\s*Date\s*[:]?\s*{date_pat}",
                date_pat,
            ])
            if inv_date:
                data["invoice_date"] = inv_date
        if not isinstance(data.get("due_date"), str) or not data.get("due_date"):
            due = first_match([
                rf"Due\s*Date\s*[:]?\s*{date_pat}",
            ])
            if due:
                data["due_date"] = due

        # Currency code
        if not isinstance(data.get("invoice_currency_code"), str) or not data.get("invoice_currency_code"):
            cur = first_match([
                r"Currency\s*[:]?\s*([A-Z]{3})\b",
                r"\b(USD|EUR|GBP|MYR|JPY|CNY|AUD|CAD|SGD|HKD|INR)\b",
            ])
            if cur:
                data["invoice_currency_code"] = cur

        # Totals (keep simple: pick first big total-looking number if empty)
        def find_amount(label_patterns):
            for lbl in label_patterns:
                m = re.search(rf"{lbl}[^\d]*(\d[\d,\.]+)", text, flags=re.IGNORECASE)
                if m:
                    return m.group(1)
            return None

        def to_float(s: Optional[str]) -> Optional[float]:
            if not s:
                return None
            try:
                return float(s.replace(",", ""))
            except Exception:
                return None

        if not data.get("total_payable_value"):
            val = to_float(find_amount(["Amount Payable", "Total Value Incl Tax", "Grand Total"]))
            if val is not None:
                data["total_payable_value"] = val
        if not data.get("total_tax_value"):
            val = to_float(find_amount(["Tax Total", "Total Tax", "GST", "SST"]))
            if val is not None:
                data["total_tax_value"] = val
        if not data.get("total_value_excl_tax"):
            val = to_float(find_amount(["Total Excl Tax", "Subtotal", "Total Value Excl Tax"]))
            if val is not None:
                data["total_value_excl_tax"] = val

        return data


class OpenAIService(BaseLLMService):
    """OpenAI GPT service for invoice parsing."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Default model fallback to avoid None triggering pydantic validation errors
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-4o')
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model=self.model,
            temperature=0.1
        )
        # Structured output parser for InvoiceData
        self.output_parser = PydanticOutputParser(pydantic_object=InvoiceData)
        
        # Load the prompt template
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the invoice parsing prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "invoice_parsing_prompt.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Prompt template not found, using default")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default prompt template."""
        return """
        You are a professional invoice data extraction expert. Extract structured data from the following invoice text:
        
        Invoice text:
        {invoice_text}
        
        Output strictly in JSON format with all required fields.
        """
    
    def _correct_tax_ids(self, source_text: str, json_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process tax_id_no to preserve letter prefixes (e.g., 'C1023...').
        If the model returned only digits but the source contains a matching
        alphanumeric token with the same numeric tail, prefer the source token.
        """
        def fix_one(value: Optional[str]) -> Optional[str]:
            if not value:
                return value
            value_str = str(value)
            # If already contains letters, keep as is
            if re.search(r"[A-Za-z]", value_str):
                return value_str
            # Digits-only: try to find letter+digits in source that ends with this digits block
            if re.fullmatch(r"\d{5,}", value_str):
                # Typical prefixes 1-3 upper letters before the same digits
                pattern = rf"\b[A-Z]{{1,3}}{re.escape(value_str)}\b"
                match = re.search(pattern, source_text)
                if match:
                    return match.group(0)
            return value_str

        for party_key in ("supplier_info", "buyer_info", "ship_to_info"):
            party = json_payload.get(party_key)
            if isinstance(party, dict):
                party["tax_id_no"] = fix_one(party.get("tax_id_no"))
        return json_payload

    def _correct_address_ocr_confusions(self, source_text: str, json_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to fix common OCR confusions in address fields by preferring
        variants that actually appear in the OCR source text. Typical swaps:
        4<->A, 0<->O, 1<->I, 5<->S, 8<->B.
        """
        swaps = [('4', 'A'), ('0', 'O'), ('1', 'I'), ('5', 'S'), ('8', 'B')]

        def best_match_address(value: Optional[str]) -> Optional[str]:
            if not value:
                return value
            v = str(value)
            # Fast path: exact appears in source
            if v in source_text:
                return v
            # Try full-string swap variants; accept first that appears in source text
            for a, b in swaps:
                if a in v:
                    cand = v.replace(a, b)
                    if cand in source_text:
                        return cand
                if b in v:
                    cand = v.replace(b, a)
                    if cand in source_text:
                        return cand
            # Try localized around slash separators (e.g., 51A/223 vs 514/223)
            parts = re.split(r"(\s|,)", v)
            rebuilt = []
            for token in parts:
                tok = token
                if '/' in tok or '-' in tok:
                    for a, b in swaps:
                        if a in tok:
                            cand = tok.replace(a, b)
                            if cand in source_text:
                                tok = cand
                                break
                        if b in tok:
                            cand = tok.replace(b, a)
                            if cand in source_text:
                                tok = cand
                                break
                rebuilt.append(tok)
            candidate = ''.join(rebuilt)
            return candidate

        for party_key in ("supplier_info", "buyer_info", "ship_to_info"):
            party = json_payload.get(party_key)
            if isinstance(party, dict):
                party["address_line1"] = best_match_address(party.get("address_line1"))
                party["address_line2"] = best_match_address(party.get("address_line2"))
        return json_payload

    def parse_invoice(self, text: str, **kwargs) -> InvoiceData:
        """Parse invoice using OpenAI GPT."""
        start_time = time.time()
        
        try:
            # Create the prompt with format instructions for strict JSON structure
            format_instructions = self.output_parser.get_format_instructions()
            prompt = self.prompt_template.format(invoice_text=text)
            messages = [
                SystemMessage(content=(
                    "You are a professional invoice data extraction expert. Output JSON only. "
                    "All fields must be present with correct types. Do not include extra explanations or markdown."
                )),
                SystemMessage(content=(
                    "Strictly follow these output format requirements. Do not output null; "
                    "use empty strings or 0 for missing values:\n" + format_instructions
                )),
                HumanMessage(content=prompt)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Parse the response
            response_text = response.content
            
            # Try to extract JSON from response
            json_data = self._extract_json_from_response(response_text)
            
            # Post-correct identifiers & addresses, enrich, fill defaults, then validate
            json_data = self._correct_tax_ids(text, json_data)
            json_data = self._correct_address_ocr_confusions(text, json_data)
            json_data = self._heuristic_enrich(text, json_data, kwargs.get('context'))
            json_data = self._fill_missing_defaults(json_data)
            invoice_data = InvoiceData(**json_data)
            
            processing_time = time.time() - start_time
            logger.info(f"OpenAI parsing completed in {processing_time:.2f} seconds")
            
            return invoice_data
            
        except Exception as e:
            logger.error(f"OpenAI parsing failed: {str(e)}")
            raise
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            raise ValueError(f"Invalid JSON response: {str(e)}")


class GoogleGeminiService(BaseLLMService):
    """Google Gemini service for invoice parsing."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro"):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        self.model = model
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=self.api_key,
            temperature=0.1
        )
        
        # Load the prompt template
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the invoice parsing prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "invoice_parsing_prompt.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Prompt template not found, using default")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default prompt template."""
        return """
        You are a professional invoice data extraction expert. Extract structured data from the following invoice text:
        
        Invoice text:
        {invoice_text}
        
        Output strictly in JSON format with all required fields.
        """
    
    def parse_invoice(self, text: str, **kwargs) -> InvoiceData:
        """Parse invoice using Google Gemini."""
        start_time = time.time()
        
        try:
            # Create the prompt
            prompt = self.prompt_template.format(invoice_text=text)
            
            # Create messages
            messages = [
                SystemMessage(content="You are a professional invoice data extraction expert. Output structured data strictly in JSON format."),
                HumanMessage(content=prompt)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Parse the response
            response_text = response.content
            
            # Try to extract JSON from response
            json_data = self._extract_json_from_response(response_text)
            
            # Fill defaults then validate and create InvoiceData
            json_data = self._fill_missing_defaults(json_data)
            invoice_data = InvoiceData(**json_data)
            
            processing_time = time.time() - start_time
            logger.info(f"Google Gemini parsing completed in {processing_time:.2f} seconds")
            
            return invoice_data
            
        except Exception as e:
            logger.error(f"Google Gemini parsing failed: {str(e)}")
            raise
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            raise ValueError(f"Invalid JSON response: {str(e)}")


class AWSBedrockService(BaseLLMService):
    """AWS Bedrock service for invoice parsing."""
    
    def __init__(self, region_name: str = "us-east-1", model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        self.region_name = region_name
        self.model_id = model_id
        
        self.llm = ChatBedrock(
            model_id=model_id,
            region_name=region_name,
            model_kwargs={"temperature": 0.1}
        )
        
        # Load the prompt template
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> str:
        """Load the invoice parsing prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "invoice_parsing_prompt.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Prompt template not found, using default")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default prompt template."""
        return """
        You are a professional invoice data extraction expert. Extract structured data from the following invoice text:
        
        Invoice text:
        {invoice_text}
        
        Output strictly in JSON format with all required fields.
        """
    
    def parse_invoice(self, text: str, **kwargs) -> InvoiceData:
        """Parse invoice using AWS Bedrock."""
        start_time = time.time()
        
        try:
            # Create the prompt
            prompt = self.prompt_template.format(invoice_text=text)
            
            # Create messages
            messages = [
                SystemMessage(content="You are a professional invoice data extraction expert. Output structured data strictly in JSON format."),
                HumanMessage(content=prompt)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Parse the response
            response_text = response.content
            
            # Try to extract JSON from response
            json_data = self._extract_json_from_response(response_text)
            
            # Fill defaults then validate and create InvoiceData
            json_data = self._fill_missing_defaults(json_data)
            invoice_data = InvoiceData(**json_data)
            
            processing_time = time.time() - start_time
            logger.info(f"AWS Bedrock parsing completed in {processing_time:.2f} seconds")
            
            return invoice_data
            
        except Exception as e:
            logger.error(f"AWS Bedrock parsing failed: {str(e)}")
            raise
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            raise ValueError(f"Invalid JSON response: {str(e)}")


class LLMServiceFactory:
    """Factory for creating LLM services."""
    
    @staticmethod
    def create_service(provider: str, **kwargs) -> BaseLLMService:
        """Create LLM service based on provider."""
        provider = provider.lower()
        
        if provider == 'openai':
            return OpenAIService(**kwargs)
        elif provider == 'google':
            return GoogleGeminiService(**kwargs)
        elif provider == 'aws':
            return AWSBedrockService(**kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")


def get_llm_service(provider: str, **kwargs) -> BaseLLMService:
    """Get LLM service instance."""
    return LLMServiceFactory.create_service(provider, **kwargs)
