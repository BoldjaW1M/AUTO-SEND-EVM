Auto Send EVM
Deskripsi
Script ini otomatis mengirim token native pada jaringan EVM. Private key diambil dari pvkeys.txt, sedangkan alamat tujuan dari address.txt. Gas fee dihitung otomatis, dan transaksi akan diulang jika gagal.

Isi pvkeys.txt dengan private key (satu per baris).
Isi address.txt dengan alamat tujuan (satu per baris).

Cara Install

pip install -r requirements.txt  


Jalankan script:

python bot.py  

Masukkan RPC URL, jumlah transaksi per wallet, dan jumlah token yang dikirim.
Transaksi berjalan otomatis.
