document.addEventListener('DOMContentLoaded', function () {
    // Synchronize Order Export filter dependencies
    var forms = document.querySelectorAll('.panel-body form');
    forms.forEach(function (form) {
        var paidOnly = form.querySelector('input[name$="-paid_only"]');
        var approvalPendingOnly = form.querySelector('input[name$="-approval_pending_only"]');
        var includePaymentAmounts = form.querySelector('input[name$="-include_payment_amounts"]');

        if (!paidOnly || !approvalPendingOnly || !includePaymentAmounts) {
            return;
        }

        function updateDisabledState(field, disabled) {
            field.disabled = disabled;
            if (disabled) {
                field.checked = false;
            }
            var boundary = field.closest('.form-group, .form-field-boundary');
            if (boundary) {
                boundary.classList.toggle('disabled', disabled);
            }
        }

        function syncOrderExportFilters() {
            updateDisabledState(approvalPendingOnly, paidOnly.checked);
            updateDisabledState(paidOnly, approvalPendingOnly.checked);
            updateDisabledState(includePaymentAmounts, approvalPendingOnly.checked);
        }

        syncOrderExportFilters();
        paidOnly.addEventListener('change', syncOrderExportFilters);
        approvalPendingOnly.addEventListener('change', syncOrderExportFilters);
    });

    // Synchronize tab clicks with URL query parameter
    var tabLinks = document.querySelectorAll('.import-export-nav-tabs a[data-toggle="tab"]');
    tabLinks.forEach(function (link) {
        link.addEventListener('click', function () {
            var target = link.getAttribute('href');
            if (target && target.indexOf('#tab-') === 0) {
                var tabName = target.replace('#tab-', '');
                var url = new URL(window.location.href);
                url.searchParams.set('tab', tabName);
                window.history.pushState({ path: url.toString() }, '', url.toString());
            }
        });
    });
});
