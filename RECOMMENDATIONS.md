# ZAP Scan Risk Assessment & Recommendations

Based on the ZAP scan findings for the static site `https://zoak.solutions`, here is a risk assessment and a list of priority recommendations.

## Implementation Status
- Removed the Google Fonts stylesheet and preconnects from HTML pages, eliminating the only external stylesheet that required SRI handling.
- Added a Content Security Policy to each HTML page and to the local nginx preview. The policy limits default resources to `self`, blocks objects and frames, uses hashes for the current inline scripts, and explicitly allows the current GitHub, RDAP, Google DNS, and ipapi endpoints used by the site.
- Added local-preview security headers for `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`, and `Permissions-Policy`.
- Left `Access-Control-Allow-Origin` unset; no CORS wildcard is configured in the repo preview or API.
- Note: production response headers still need to be configured at the deployed HTTPS edge because GitHub Pages does not read this local nginx preview configuration.

## Risk Assessment
Given that `https://zoak.solutions` is a **static HTML site** with no backend application processing user input, the overall risk profile is significantly lower than that of a dynamic web application. Vulnerabilities like SQL Injection or Reflected XSS are not applicable. 

However, there are still risks associated with third-party resource loading and missing defense-in-depth security headers. Most of the findings reported by ZAP are informational or low-risk for a static site, but a few represent best practices that should be implemented to prevent potential supply-chain attacks or client-side issues.

### Low Risk / Informational Findings
- **Base64 Disclosure**: Likely a false positive. Base64 strings are often used for inline images or hashes.
- **Cache-control / Storable Content**: Purely informational. Static sites are meant to be cached.
- **Sec-Fetch-* Headers Missing**: Browser request headers, not server misconfigurations.
- **COEP / COOP Missing**: Low risk for a basic static site not using advanced features like SharedArrayBuffer.
- **Permissions Policy Header Not Set**: Good practice, but low risk if the site doesn't use device features (camera, mic, geolocation).

## Priority Recommendations

The following recommendations address the most relevant findings that could present a risk even to a static site:

### 1. Implement Sub Resource Integrity (SRI)
**Finding:** Sub Resource Integrity Attribute Missing
**Risk Level:** Medium
**Reasoning:** If the static site loads third-party scripts or stylesheets (e.g., from a public CDN like unpkg, cdnjs), compromising that CDN could allow attackers to inject malicious code into your site.
**Recommendation:** Add `integrity` and `crossorigin` attributes to all external `<script>` and `<link>` tags. 
*Example:*
```html
<script src="https://example-cdn.com/library.js" integrity="sha384-..." crossorigin="anonymous"></script>
```

### 2. Configure a Basic Content Security Policy (CSP)
**Finding:** Content Security Policy (CSP) Header Not Set / CSP: Failure to Define Directive with No Fallback / CSP: style-src unsafe-inline
**Risk Level:** Low-Medium
**Reasoning:** Even on a static site, a CSP provides a strong layer of defense against unauthorized script execution or data exfiltration if the site is somehow compromised or if an included third-party script acts maliciously.
**Recommendation:** Set up a restrictive CSP header. At a minimum, restrict resources to the same origin and explicitly whitelist any required third-party domains.
*Example Header:*
`Content-Security-Policy: default-src 'self'; style-src 'self'; img-src 'self' data:;`

*Note: Avoid using `'unsafe-inline'` for styles or scripts as it weakens the CSP. If inline styles are strictly required, consider using hashes or nonces.*

### 3. Review Cross-Domain Misconfigurations (CORS)
**Finding:** Cross-Domain Misconfiguration
**Risk Level:** Low
**Reasoning:** Ensure that your CORS headers (`Access-Control-Allow-Origin`) are not set to `*` if you serve sensitive static assets, though for a public static site, this is typically not a significant issue.
**Recommendation:** Restrict `Access-Control-Allow-Origin` to specific trusted domains if API calls or cross-origin resource sharing is intended. If not, ensure it is omitted or strictly configured.

### 4. Implement Basic Security Headers
**Recommendation:** While not explicitly detailed in high-severity ZAP findings, ensure that your hosting provider (e.g., GitHub Pages, AWS S3+CloudFront, Netlify) is configured to return other standard security headers to protect users:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` (or `SAMEORIGIN`)
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
