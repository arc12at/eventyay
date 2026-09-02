$(function () {
    "use strict";

    var update_currency = function () {
        var currency = $("#id_currency").val() || "";
        $(".currency-addon").text(currency);
        $("#review-currency").text(currency);
    };

    var update_tickets_and_capacity = function () {
        var total_capacity = 0;
        var has_infinite = false;
        var total_tickets = 0;
        var paid_tickets = 0;
        var free_tickets = 0;

        $("#ticket-type-formset [data-formset-form]").each(function () {
            var $row = $(this);
            var is_deleted = $row.find("input[name$=DELETE]").prop("checked");
            if (is_deleted || $row.css("display") === "none") {
                return;
            }

            total_tickets += 1;

            // Price calculation
            var price_str = ($row.find("input[name$=default_price]").val() || "").trim().replace(",", ".");
            var price_num = parseFloat(price_str);
            var is_paid = !isNaN(price_num) && price_num > 0;

            if (is_paid) {
                paid_tickets += 1;
                $row.find(".col-status").html('<span class="quickstart-status-badge badge-paid">Paid</span>');
            } else {
                free_tickets += 1;
                $row.find(".col-status").html('<span class="quickstart-status-badge badge-free">Free</span>');
            }

            // Quota calculation
            var quota_val = ($row.find("input[name$=quota]").val() || "").trim();
            if (quota_val === "") {
                has_infinite = true;
            } else if (!has_infinite) {
                var q = parseInt(quota_val, 10);
                if (!isNaN(q)) {
                    total_capacity += q;
                }
            }
        });

        var cap_text = has_infinite || total_tickets === 0 ? "∞" : total_capacity.toString();
        $("#total-capacity").text(cap_text);
        $("#review-total-capacity").text(cap_text);
        $("#review-ticket-types").text(total_tickets);
        $("#review-paid-tickets").text(paid_tickets);
        $("#review-free-tickets").text(free_tickets);

        // Toggle payment section visibility based on whether paid tickets exist
        if (paid_tickets > 0) {
            $("#payment-free-state").hide();
            $("#payment-methods-selection").show();
        } else {
            $("#payment-free-state").show();
            $("#payment-methods-selection").hide();
        }

        update_review_summary();
    };

    var update_review_summary = function () {
        // Currency
        var currency = $("#id_currency").val() || "";
        $("#review-currency").text(currency);

        // Login required
        var login_req = $("#id_require_registered_account_for_tickets").is(":checked");
        $("#review-login-required").text(login_req ? gettext("Yes") : gettext("No"));

        // Waiting list
        var waiting_list = $("#id_waiting_list_enabled").is(":checked");
        $("#review-waiting-list").text(waiting_list ? gettext("Enabled") : gettext("Disabled"));

        // Ticket download
        var ticket_dl = $("#id_ticket_download").is(":checked");
        $("#review-ticket-downloads").text(ticket_dl ? gettext("Enabled") : gettext("Disabled"));

        // Payment methods
        var selected_methods = [];
        if ($("#id_payment_banktransfer__enabled").is(":checked")) {
            selected_methods.push(gettext("Bank transfer"));
        }
        if ($("#id_payment_manualpayment__enabled").is(":checked")) {
            selected_methods.push(gettext("Manual payment"));
        }
        if ($("#id_payment_stripe__enabled").is(":checked")) {
            selected_methods.push(gettext("Stripe"));
        }
        if ($("#id_payment_paypal__enabled").is(":checked")) {
            selected_methods.push(gettext("PayPal"));
        }

        if (selected_methods.length > 0) {
            $("#review-payment-methods").text(selected_methods.join(", "));
        } else {
            $("#review-payment-methods").text(gettext("None selected"));
        }
    };

    // Currency change
    $("#id_currency").on("change", function () {
        update_currency();
    });

    // Inputs change for live calculations
    $("#ticket-type-formset").on("change input keyup", "input", function () {
        update_tickets_and_capacity();
    });

    // Formset row added or deleted
    $("[data-formset]").on("formAdded", function (e) {
        update_currency();
        update_tickets_and_capacity();
    });

    $("#ticket-type-formset").on("click", "[data-formset-delete-button]", function () {
        setTimeout(update_tickets_and_capacity, 50);
    });

    // Feature and checkout checkboxes change
    $("#id_require_registered_account_for_tickets, #id_waiting_list_enabled, #id_ticket_download, #id_show_quota_left, #id_attendee_names_required").on("change", function () {
        update_review_summary();
    });

    // Payment tile clicks
    $(".payment-tile").on("click", function (e) {
        if ($(e.target).is("input[type=checkbox]")) {
            return;
        }
        var $checkbox = $(this).find("input[type=checkbox]");
        $checkbox.prop("checked", !$checkbox.prop("checked")).trigger("change");
    });

    $(".payment-tile input[type=checkbox]").on("change", function () {
        var $tile = $(this).closest(".payment-tile");
        if ($(this).is(":checked")) {
            $tile.addClass("selected");
        } else {
            $tile.removeClass("selected");
        }

        // Toggle bank transfer details if applicable
        if ($(this).attr("id") === "id_payment_banktransfer__enabled") {
            if ($(this).is(":checked")) {
                $("#banktransfer-details-box").slideDown();
            } else {
                $("#banktransfer-details-box").slideUp();
            }
        }

        update_review_summary();
    });

    // Total capacity override toggle
    $("#total-capacity-edit").on("click", function (e) {
        e.preventDefault();
        var current_cap = $("#total-capacity").text();
        if (current_cap !== "∞") {
            $("#id_total_quota").val(parseInt(current_cap, 10));
        }
        $("#total-capacity").hide();
        $("#id_total_quota").closest("div").removeClass("sr-only");
        $("#total-capacity-edit").hide();
    });

    // Stepper navigation & smooth scroll
    $(".quickstart-step-item").on("click", function (e) {
        e.preventDefault();
        var target = $(this).attr("href");
        var $target = $(target);
        if ($target.length) {
            $(".quickstart-step-item").removeClass("active");
            $(this).addClass("active");
            $("html, body").animate({
                scrollTop: $target.offset().top - 80
            }, 300);
        }
    });

    // Edit setup button scrolls to top/step-currency
    $("#btn-edit-setup").on("click", function (e) {
        e.preventDefault();
        $(".quickstart-step-item").removeClass("active");
        $('.quickstart-step-item[data-step="1"]').addClass("active");
        $("html, body").animate({
            scrollTop: $("#step-currency").offset().top - 80
        }, 300);
    });

    // Initialize state on page load
    update_currency();
    update_tickets_and_capacity();
    update_review_summary();
});
