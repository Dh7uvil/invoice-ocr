document.addEventListener('DOMContentLoaded', function () {
  var partyType = document.getElementById('id_party_type');
  if (!partyType) return;

  function sel(id) { return document.getElementById(id); }

  // Live values pulled from server for this invoice_data
  var serverValues = null;
  var currentType = partyType.value;

  function writeFields(data) {
    if (!data) return;
    var m = {
      'id_name': data.name,
      'id_address_line1': data.address_line1,
      'id_address_line2': data.address_line2,
      'id_country_code': data.country_code,
      'id_tax_id_no': data.tax_id_no,
      'id_registration_no': data.registration_no,
      'id_contact_number': data.contact_number
    };
    Object.keys(m).forEach(function (k) {
      var el = sel(k);
      if (el !== null && el !== undefined) el.value = m[k] || '';
    });
  }

  function fetchServerValues(cb) {
    // Try to get invoice_data id from hidden related field in the admin change form
    // Django admin renders a link near the raw id field; we fallback to regex from breadcrumb
    var link = document.querySelector('a[href*="/admin/ocr_app/invoicedata/"]');
    var invoiceId = null;
    if (link) {
      var m = link.getAttribute('href').match(/invoicedata\/(\d+)/);
      if (m) invoiceId = m[1];
    }
    if (!invoiceId) {
      // Try to parse from page HTML
      var html = document.documentElement.innerHTML;
      var m2 = html.match(/invoicedata\/(\d+)\//);
      if (m2) invoiceId = m2[1];
    }
    if (!invoiceId) { cb && cb(null); return; }

    var url = '/api/parties/' + invoiceId + '/';
    fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) { serverValues = data || {}; cb && cb(serverValues); })
      .catch(function () { cb && cb(null); });
  }

  // Initialize: fetch from server, then set fields matching current type (if available)
  fetchServerValues(function () {
    if (serverValues && serverValues[currentType]) {
      writeFields(serverValues[currentType]);
    }
  });

  partyType.addEventListener('change', function () {
    currentType = partyType.value;
    if (serverValues && serverValues[currentType]) {
      writeFields(serverValues[currentType]);
    } else {
      // No server value for this type -> clear
      writeFields({ name: '', address_line1: '', address_line2: '', country_code: '', tax_id_no: '', registration_no: '', contact_number: '' });
    }
  });
});


