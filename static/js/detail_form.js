// static/js/detail_form.js (VERSI KOD PENUH TERAKHIR)

document.addEventListener('DOMContentLoaded', function() {
    // Dapatkan elemen utama (container untuk baris-baris item)
    const itemList = document.getElementById('item_list');
    const addItemButton = document.getElementById('add_item');
    
    // Template HTML untuk dropdown saiz
    const saizDropdownHTML = `
        <select class="form-select form-select-sm saiz-input" name="saiz[]" required>
            <option value="">Pilih Saiz</option>
            <option value="XS">XS</option>
            <option value="S">S</option>
            <option value="M">M</option>
            <option value="L">L</option>
            <option value="XL">XL</option>
            <option value="2XL">2XL</option>
            <option value="3XL">3XL</option>
            <option value="4XL">4XL</option>
            <option value="5XL">5XL</option>
        </select>
    `;

    // Fungsi untuk mengemas kini keadaan butang 'Padam'
    function updateRemoveButtons() {
        if (!itemList) return; 

        const rows = itemList.querySelectorAll('.item-row');
        rows.forEach(row => {
            const removeButton = row.querySelector('.remove-item');
            
            // Tunjukkan butang remove hanya jika ada lebih dari 1 baris
            if (rows.length > 1) {
                // Pastikan ia dipaparkan sebagai block/inline-block
                removeButton.style.display = 'inline-block'; 
            } else {
                // Sembunyikan untuk baris tunggal
                removeButton.style.display = 'none'; 
            }
        });
    }

    // FUNGSI UTAMA TAMBAH BARIS
    function addNewRow() {
        if (!itemList) return;

        const newRow = document.createElement('div');
        // Gunakan g-2 untuk jarak antara kolum (Bootstrap 5)
        newRow.classList.add('row', 'mb-3', 'item-row', 'g-2'); 

        // Membina HTML untuk baris baru
        newRow.innerHTML = `
            <div class="col-4">
                <input type="text" class="form-control form-control-sm" name="pemain_nama[]" placeholder="Nama">
            </div>
            <div class="col-3">
                <input type="text" class="form-control form-control-sm" name="jersi_no[]" placeholder="No Jersi">
            </div>
            <div class="col-3">
                ${saizDropdownHTML}
            </div>
            <div class="col-2 text-center">
                <button type="button" class="btn btn-danger btn-sm remove-item"><i class="fas fa-minus"></i></button>
            </div>
        `;
        itemList.appendChild(newRow); 
        updateRemoveButtons(); 
    }

    // 1. BINDING untuk butang Tambah Item Baris (+)
    if (addItemButton) {
        addItemButton.addEventListener('click', addNewRow);
    }
    
    // 2. BINDING PENGHAPUSAN (Menggunakan Event Delegation)
    // Ini membolehkan butang padam berfungsi pada baris yang ditambah secara dinamik
    document.body.addEventListener('click', function(e) {
        const targetElement = e.target.closest('.remove-item');
        if (targetElement) {
            const rowToRemove = targetElement.closest('.item-row');
            
            // Dapatkan semua baris item yang ada
            const allRows = itemList.querySelectorAll('.item-row');
            
            // Hanya padam jika ada lebih daripada satu baris
            if (rowToRemove && allRows.length > 1) { 
                rowToRemove.remove();
                updateRemoveButtons(); 
            } else if (rowToRemove) {
                 // Jika hanya satu baris, hanya clear input, jangan padam
                 const inputs = rowToRemove.querySelectorAll('input, select');
                 inputs.forEach(input => {
                    if (input.name.includes('saiz')) {
                        input.value = ''; // Reset dropdown saiz
                    } else {
                        input.value = ''; // Clear input teks
                    }
                 });
                 // Anda boleh buang alert() ini untuk presentation, tetapi ia berguna untuk debugging.
                 // alert("Anda mesti mempunyai sekurang-kurangnya satu baris pesanan. Input telah dikosongkan.");
            }
        }
    });

    // Panggilan awal untuk menetapkan status butang padam pada pemuatan halaman
    updateRemoveButtons();
});