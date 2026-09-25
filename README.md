# Rotom — Smart Document Scanner & OCR Service

Rotom adalah sistem pemindai dokumen cerdas berbasis **Python**, **OpenCV**, dan **C++ Native Acceleration** yang dirancang untuk mendeteksi kartu nama (*business card*), mengoreksi distorsi perspektif, membersihkan citra, serta melakukan ekstraksi teks terstruktur berbasis OCR.

---

## Cara Menginstall & Menjalankan

### Menggunakan Docker (Direkomendasikan)

1. **Build Docker Image**:
   ```bash
   docker build -t rotom-scanner .