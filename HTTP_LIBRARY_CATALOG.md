# NiP HTTP Client Library Catalog (Observed in Analysis Output)

This catalog is derived from `nip_analyzer_output.csv` (column **HTTP Libraries**). It lists every HTTP client library identifier that NiP detected at least once in the analyzed repositories.

**Note:** Entries like `None detected` in the CSV indicate that NiP did not detect an HTTP client library in that repository; they are treated as *no-library* markers (not as libraries) and are excluded from the catalog below.

## Dataset coverage
- Total repositories in CSV: **17,410**
- Repositories with ≥1 detected HTTP library: **14,631** (84.0%)
- Repositories with no detected HTTP library: **2,779** (16.0%)
- Unique HTTP library identifiers observed: **49**

## How to interpret “Top repo languages”
For each library, we report the most common repository languages (from the CSV **Languages** column) among repositories where the library was detected. Because repositories may contain multiple languages, these co-occurrence counts can exceed the number of repositories for that library.

## Top 20 libraries by repository coverage
| Library | #Repos | %Repos | Top repo languages (co-occurrence) |
|---|---:|---:|---|
| `fetch` | 6656 | 38.23% | javascript (6476); typescript (2490); python (1745) |
| `axios` | 5472 | 31.43% | javascript (5246); typescript (2273); python (1027) |
| `requests` | 4647 | 26.69% | python (4647); javascript (2167); typescript (480) |
| `urllib` | 3096 | 17.78% | python (3096); javascript (2054); typescript (839) |
| `urllib.request` | 1887 | 10.84% | python (1887); javascript (1552); typescript (535) |
| `http.client` | 1526 | 8.77% | python (1526); javascript (1355); typescript (430) |
| `aiohttp` | 1347 | 7.74% | python (1347); javascript (1030); typescript (103) |
| `urllib3` | 1193 | 6.85% | python (1193); javascript (1080); typescript (215) |
| `node-fetch` | 1165 | 6.69% | javascript (1162); typescript (859); python (641) |
| `http` | 1137 | 6.53% | javascript (1121); typescript (710); python (592) |
| `request` | 943 | 5.42% | javascript (943); typescript (581); python (527) |
| `https` | 817 | 4.69% | javascript (817); typescript (600); python (419) |
| `got` | 732 | 4.20% | javascript (732); typescript (700); python (599) |
| `URLSession` | 710 | 4.08% | swift (710); javascript (376); typescript (333) |
| `urllib2` | 614 | 3.53% | python (614); javascript (555); typescript (420) |
| `httplib` | 541 | 3.11% | python (541); javascript (519); typescript (392) |
| `ktor` | 484 | 2.78% | kotlin (484); swift (407); javascript (108) |
| `OkHttp` | 478 | 2.75% | java (310); kotlin (259); javascript (222) |
| `net/http` | 464 | 2.67% | ruby (262); go (215); javascript (135) |
| `httpx` | 460 | 2.64% | python (460); javascript (404); typescript (13) |

## Complete catalog (all observed libraries)
Sorted by repository coverage (desc), then name.

| Library | #Repos | %Repos | Top repo languages (co-occurrence) |
|---|---:|---:|---|
| `fetch` | 6656 | 38.23% | javascript (6476); typescript (2490); python (1745) |
| `axios` | 5472 | 31.43% | javascript (5246); typescript (2273); python (1027) |
| `requests` | 4647 | 26.69% | python (4647); javascript (2167); typescript (480) |
| `urllib` | 3096 | 17.78% | python (3096); javascript (2054); typescript (839) |
| `urllib.request` | 1887 | 10.84% | python (1887); javascript (1552); typescript (535) |
| `http.client` | 1526 | 8.77% | python (1526); javascript (1355); typescript (430) |
| `aiohttp` | 1347 | 7.74% | python (1347); javascript (1030); typescript (103) |
| `urllib3` | 1193 | 6.85% | python (1193); javascript (1080); typescript (215) |
| `node-fetch` | 1165 | 6.69% | javascript (1162); typescript (859); python (641) |
| `http` | 1137 | 6.53% | javascript (1121); typescript (710); python (592) |
| `request` | 943 | 5.42% | javascript (943); typescript (581); python (527) |
| `https` | 817 | 4.69% | javascript (817); typescript (600); python (419) |
| `got` | 732 | 4.20% | javascript (732); typescript (700); python (599) |
| `URLSession` | 710 | 4.08% | swift (710); javascript (376); typescript (333) |
| `urllib2` | 614 | 3.53% | python (614); javascript (555); typescript (420) |
| `httplib` | 541 | 3.11% | python (541); javascript (519); typescript (392) |
| `ktor` | 484 | 2.78% | kotlin (484); swift (407); javascript (108) |
| `OkHttp` | 478 | 2.75% | java (310); kotlin (259); javascript (222) |
| `net/http` | 464 | 2.67% | ruby (262); go (215); javascript (135) |
| `httpx` | 460 | 2.64% | python (460); javascript (404); typescript (13) |
| `cross-fetch` | 437 | 2.51% | javascript (431); typescript (424); swift (297) |
| `Fuel` | 251 | 1.44% | kotlin (251); java (84); javascript (72) |
| `Retrofit` | 251 | 1.44% | kotlin (251); java (84); javascript (72) |
| `http4k` | 229 | 1.32% | kotlin (229); java (84); javascript (55) |
| `HttpClient` | 179 | 1.03% | java (179); javascript (63); typescript (20) |
| `HttpURLConnection` | 135 | 0.78% | java (135); javascript (88); python (70) |
| `URLRequest` | 122 | 0.70% | swift (122); javascript (18); python (17) |
| `RestTemplate` | 112 | 0.64% | java (112); javascript (68); python (28) |
| `github.com/parnurzeal/gorequest` | 84 | 0.48% | go (84); python (12) |
| `Apache HttpClient` | 66 | 0.38% | java (66); javascript (44); python (27) |
| `isomorphic-fetch` | 43 | 0.25% | javascript (40); python (34); typescript (8) |
| `superagent` | 43 | 0.25% | javascript (40); typescript (35); python (25) |
| `needle` | 40 | 0.23% | javascript (40); ruby (36); typescript (36) |
| `httplib2` | 37 | 0.21% | python (37); javascript (25); typescript (10) |
| `excon` | 36 | 0.21% | ruby (36); javascript (36); typescript (36) |
| `open-uri` | 35 | 0.20% | ruby (35); javascript (32); python (12) |
| `rest-client` | 35 | 0.20% | ruby (35); javascript (29); typescript (13) |
| `RestSharp` | 34 | 0.20% | csharp (34); javascript (21); python (11) |
| `tornado.httpclient` | 34 | 0.20% | javascript (34); python (34); ruby (6) |
| `undici` | 30 | 0.17% | javascript (30); python (25); typescript (14) |
| `Alamofire` | 19 | 0.11% | swift (19); javascript (3); kotlin (1) |
| `httparty` | 17 | 0.10% | ruby (17); javascript (16); go (9) |
| `node:http` | 14 | 0.08% | javascript (14); typescript (8); python (4) |
| `WebClient` | 9 | 0.05% | java (9); javascript (8); typescript (4) |
| `faraday` | 8 | 0.05% | ruby (8); javascript (7) |
| `Refit` | 5 | 0.03% | csharp (5); javascript (2) |
| `Flurl.Http` | 3 | 0.02% | csharp (3) |
| `java.net.http.HttpClient` | 1 | 0.01% | javascript (1); kotlin (1); python (1) |
| `Moya` | 1 | 0.01% | swift (1) |
