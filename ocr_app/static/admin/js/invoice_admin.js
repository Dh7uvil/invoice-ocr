/**
 * Invoice OCR Admin JavaScript
 * Enhanced file upload experience
 */

(function($) {
    'use strict';
    
    $(document).ready(function() {
        // File upload handling
        $('input[type="file"]').on('change', function() {
            var file = this.files[0];
            if (file) {
                // Show file info
                var fileName = file.name;
                var fileSize = formatFileSize(file.size);
                var filePath = 'media/invoices/' + fileName;
                
                // Update hidden fields
                $('#id_file_name').val(fileName);
                $('#id_file_path').val(filePath);
                $('#id_file_size').val(file.size);
                
                // Display file info
                showFileInfo(fileName, fileSize, filePath);
            }
        });
        
        // Display file info
        function showFileInfo(name, size, path) {
            var infoHtml = '<div class="file-info" style="margin-top: 10px; padding: 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;">' +
                '<h4>File Information</h4>' +
                '<p><strong>File name:</strong> ' + name + '</p>' +
                '<p><strong>File size:</strong> ' + size + '</p>' +
                '<p><strong>File path:</strong> ' + path + '</p>' +
                '</div>';
            
            // Remove previous file info
            $('.file-info').remove();
            
            // Add new file info
            $('input[type="file"]').after(infoHtml);
        }
        
        // Format file size
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            var k = 1024;
            var sizes = ['Bytes', 'KB', 'MB', 'GB'];
            var i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        // Processing configuration suggestions
        $('select[name="ocr_engine"]').on('change', function() {
            var engine = $(this).val();
            var llmProvider = $('select[name="llm_provider"]');
            
            // Recommend LLM provider based on OCR engine
            if (engine === 'google_document_ai') {
                llmProvider.val('google');
            } else if (engine === 'aws_textract') {
                llmProvider.val('aws');
            } else {
                llmProvider.val('openai');
            }
        });
        
        // Add process button
        if ($('#id_status').length && $('#id_status').val() === 'pending') {
            var processButton = '<button type="button" class="btn btn-primary" id="process-invoice-btn" style="margin-top: 10px;">Start Processing Invoice</button>';
            $('input[name="_save"]').after(processButton);
            
            $('#process-invoice-btn').on('click', function() {
                if (confirm('Are you sure you want to start processing this invoice?')) {
                    // AJAX call to start processing can be added here
                    alert('Processing started. Check back shortly for results.');
                }
            });
        }
    });
})(django.jQuery);
