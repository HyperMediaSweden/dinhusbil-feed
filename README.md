# dinhusbil-feed

Adnami-feeds med husbilar i lager från [dinhusbil.nu](https://dinhusbil.nu), per anläggning.
Datan hämtas från Empori DSO-API:et (`https://dinhusbil.dso.empori.se/dsoApi/v1/objects`) varje timme
av GitHub Actions och publiceras via GitHub Pages från mappen `docs/`.

**Feed-adresser** (klistras in som feed i Adnami, max 50 rader):

- https://hypermediasweden.github.io/dinhusbil-feed/feed-frillesas.xml
- https://hypermediasweden.github.io/dinhusbil-feed/feed-jonkoping.xml
- https://hypermediasweden.github.io/dinhusbil-feed/feed-vaxjo.xml
- https://hypermediasweden.github.io/dinhusbil-feed/feed-bockara.xml

Översikt och senaste körning: https://hypermediasweden.github.io/dinhusbil-feed/

**Mappning i Adnami (Dynamic Fluid Product Carousel):** Product Click URL = `url`, Product Image = `image_url`,
Product Text = `title` (eller `text`), Product Price = `price`.

Kör manuellt: fliken Actions → "Uppdatera feeds" → Run workflow. Lokalt: `python3 generate_feeds.py`.
Ändra anläggningar eller fordonstyp överst i `generate_feeds.py`.
