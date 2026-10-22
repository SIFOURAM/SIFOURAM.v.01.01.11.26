# Receipt Image Integration Testing Plan

## Image Handling
- Use only JPEG, PNG, or WEBP images encoded as base64.
- Use a non-uniform real receipt or payment-proof image with legible visual features.
- Detect the actual MIME type after any transform.
- Resize large images before submission and reject unsupported, blank, or animated inputs.

## Validation Cases
1. Upload a real receipt image and confirm AI returns a structured draft only.
2. Verify date, vendor, amount, paid method, and line items can be corrected before saving.
3. Verify malformed base64, unsupported MIME types, and blank images return clear errors.
4. Confirm the stored proof URL and extracted fields are visible only to permitted roles.
5. Test manual entry remains usable when AI extraction fails.
6. Run tests with base64 image payloads only; do not use SVG, GIF, BMP, HEIC, or blank images.