# Dextra Operations Team

Tim operasional lintas domain: permintaan dipecah ke finance, HR, dan inventory, tiap spesialis menghasilkan output bersumbernya sendiri, lalu koordinator mengonsolidasi satu laporan. Tidak ada anggota yang menyetujui atau mengeksekusi.

## 类型

Team 型（多角色协作团队）

## 功能

- **Dekomposisi lintas domain** — Operations Coordinator memecah permintaan menjadi bagian finance, HR, dan inventory dengan cakupan (pertanyaan, periode, output) yang jelas.
- **Eksekusi paralel** — tiga spesialis bekerja independen dan mengembalikan hasil lewat SendMessage; tidak ada komunikasi langsung antar anggota.
- **Verifikasi silang** — koordinator memeriksa setiap angka punya sumber, dan menampilkan konflik antar domain (mis. headcount HR vs basis payroll Finance) sebagai konflik, bukan memilih salah satu.
- **Konsolidasi** — satu laporan: ringkasan, per domain, konflik, sumber, klarifikasi, bagian belum lengkap, dan catatan governance.
- **Batas governance** — tidak ada anggota yang menyetujui plan, membuat approval/mandate, atau mengeksekusi tindakan eksternal; tindakan sensitif wajib policy check + approval manusia dan tercatat di audit trail.

## 使用示例

- "Susun review operasional bulan ini — ambil dari finance, HR, dan inventory, sebutkan sumbernya."
- "Dua departemen melaporkan jumlah karyawan berbeda — tampilkan keduanya dengan sumber, jangan pilih sendiri."
- "Materi mana yang di bawah reorder point, dan apa dampaknya ke biaya bulan ini?"

## 头像

头像已自动生成在 `avatars/` 目录下。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到专家目录下：

```
C:\Users\Atmint\.workbuddy-ai\plugins\marketplaces\my-experts\plugins/dextra-operations-team/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
zip -r dextra-operations-team.zip dextra-operations-team/
```
