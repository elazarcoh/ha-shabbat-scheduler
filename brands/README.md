# Brand assets

Prepared for submission to `home-assistant/brands`, which this repo
cannot submit to directly - it is reviewed by Home Assistant's own brand
team via a pull request against their repository, not this one.

The mark is an original, simple geometric drawing of two lit Shabbat
candles - generated with Pillow (see the implementation plan's Task 8
for the generator script), not borrowed from any other project or
brand.

To submit:

1. Fork `https://github.com/home-assistant/brands`.
2. Copy these four files to
   `custom_integrations/shabbat_scheduler/` in that fork
   (`icon.png`, `icon@2x.png`, `logo.png`, `logo@2x.png`).
3. Open a pull request against `home-assistant/brands`, following the
   image specification in that repo's `README.md` (there is currently
   no separate `CONTRIBUTING.md`; the "Image specification" section of
   the root `README.md` is the source of truth as of this writing).
4. Once merged, the integration's icon appears automatically in Home
   Assistant's UI for anyone on a recent core version - no change
   needed in this repo.

Note: as of Home Assistant 2026.3.0, custom integrations can also
bundle their brand icons directly via the Brands Proxy API instead of
(or ahead of) a `home-assistant/brands` submission - see the
[Brands Proxy API announcement](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api).
That is a separate, newer option not implemented by this task; the
`home-assistant/brands` submission above remains valid regardless.

Until either path lands, Home Assistant falls back to a generic
integration icon. That is expected and not a bug in this integration.

## Image specification (as fetched from `home-assistant/brands`)

- All four files are PNG with transparent backgrounds.
- `icon.png`: 256x256. `icon@2x.png`: 512x512 (both square, 1:1).
- `logo.png` / `logo@2x.png`: since this mark is square (icon and logo
  are the same artwork), both are also 256x256 / 512x512, which
  satisfies the logo rule that the shortest side be no larger than
  256px (512px for @2x) and no smaller than 128px (256px for @2x).
  Per that repo's own README, a brand whose logo is square only needs
  to supply the icon files - the icon is used as the logo fallback -
  but this task ships explicit `logo.png` / `logo@2x.png` copies as
  the plan specifies.
