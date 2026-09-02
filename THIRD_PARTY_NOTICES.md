# Third-party data notices

## OMAI assignment recipe collection

The application uses the recipe archive supplied in OMAI's public take-home repository:

- source: <https://github.com/OMAI-dev/arbetsprov-recept>
- file: `20170107-061401-recipeitems.json.zip`
- pinned SHA-256: `4149d2d8677f26323b6da0300014c155abe1ba1f78af2c5c8e4f63f0b7df57f1`

The upstream repository does not currently declare a software or data license. The collection is
used here only for the requested assignment and should not be assumed to be licensed for unrelated
commercial redistribution.

## Recipe Box instruction corpus

The build uses the Allrecipes and Epicurious exports from Recipe Box solely to recover methods for
strictly matching OMAI records:

- source mirror: <https://github.com/kz882/recipe>
- pinned commit: `9db77df8c52c454f83dd2d6bdcde4580e3298498`
- `recipes_raw_nosource_ar.json` SHA-256:
  `93da2202eacb85ad81b50e49f9c1ceba33eb298f1c82a6d02eb59cab7d550cb5`
- `recipes_raw_nosource_epi.json` SHA-256:
  `08c7c8103a9c0dd114dc3fe01490fdf86ec9dee05d4db7d96504a61b5e8a886e`
- bundled license SHA-256:
  `749689720d9b800da61e4a2936af9dd7df78ac6914181f04cab41b0ce5485eff`

The included Recipe Box notice is the Open Data Commons Attribution License. It licenses database
rights and explicitly warns that rights in individual contents may be separate. Method text remains
attributable to the source publishers. This demonstration must not be represented as a cleared
commercial recipe catalog without confirming those content rights.

Recipe Box project attribution: Ryan Lee, <https://github.com/rtlee9/recipe-box>.
