const radios = document.querySelectorAll('.rating-stars input[type="radio"]');
let selectedRadio = Array.from(radios).find(r => r.checked) || null;

radios.forEach(radio => {
    radio.addEventListener('click', () => {
        if (selectedRadio === radio) {
            radio.checked = false;
            selectedRadio = null;
        } else {
            selectedRadio = radio;
        }
    });
});
