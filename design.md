# design.md

Sumber kebenaran visual DEXTRA. Semua token berasal dari `packages/design-system`
dan dikonsumsi lewat `packages/ui`.

> Status: kerangka. Nilai token final menyusul.

## Prinsip

- **Calm & governed.** Antarmuka tenang, rapi, dan terasa terkendali — bukan ramai.
- **AI sebagai rekan kerja.** WorkBuddy selalu terlihat, tetapi tidak mendominasi.
- **Governance terlihat.** Approval, risiko, dan audit adalah bagian UI, bukan tersembunyi.
- **Kepadatan data yang manusiawi.** Tabel padat, tetapi hierarki dan spacing jelas.
- **Konsisten.** Tidak ada warna, radius, atau spacing di luar token.

## Lapisan

```text
design-system  →  tokens, colors, typography, spacing, themes
ui             →  components, forms, tables, dialogs, charts
features       →  komposisi per domain
```

## Token (rencana)

| Kategori   | Lokasi                              |
| ---------- | ----------------------------------- |
| Color      | `packages/design-system/src/colors` |
| Typography | `packages/design-system/src/typography` |
| Spacing    | `packages/design-system/src/spacing` |
| Tokens     | `packages/design-system/src/tokens` |
| Themes     | `packages/design-system/src/themes` |

## Aturan

- Jangan hardcode warna/spacing di komponen; pakai token.
- Komponen lintas halaman masuk `packages/ui`; komponen spesifik halaman masuk `apps/web/src/features`.
- Seluruh state penting (loading, empty, error, denied) wajib punya desain.
