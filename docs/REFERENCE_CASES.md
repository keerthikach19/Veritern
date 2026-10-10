# Five-company reference reviews

The reference library makes the presentation independent of network access. It contains the **text patterns and case notes supplied by the project owner on 10 October 2026**. It does not contain original offer-letter images, authenticated letters, scraped participant reports, or recorded model responses.

Enable locally in `.env` and restart Streamlit:

```dotenv
REFERENCE_CASES_ENABLED=true
```

The switch is deliberately a boolean, not a fake API credential. `.env` stays ignored by Git. A fresh checkout defaults to the normal website-review path and accurately reports missing provider configuration; it never manufactures a quota error. Anyone can reproduce the reference presentation by enabling the documented switch.

Enter a listed URL, confirm the scope and leave **Use provided reference text** checked. Or open a case from the library. Uncheck that option to run the actual website pipeline. These paths are separate: live results are never silently replaced with prepared company material.

| URL / domain | Reference | Result for supplied material |
| --- | --- | --- |
| `internpe.in` | InternPE | Suspicious — verification required |
| `internshipstudio.com` | Internship Studio | Suspicious — verification required |
| `oasisinfobyte.com`, `oasisinfobyte.in` | Oasis Infobyte | Suspicious — verification required |
| `tcs.com` (including `/careers`) | TCS-branded appointment reference | Suspicious — verification required |
| `careers.wipro.com`, `wipro.com` | Wipro-branded partial appointment reference | Unknown; structured terms are positive indicators, authenticity unverified |

These labels concern the **supplied, unverified reference material**, not all offers from those companies. A URL selects a reference; it does not establish that the website issued the described letter. Unknown and lookalike domains do not receive another company's result.

## Evidence mapping

All data is in `src/veritern/data/reference_cases.json`. Every note has an exact quotation from that case's `reference_text`; the Pydantic loader rejects unsupported quotations and identifying phrases. Text describing a missing term or a badge is attributed to the supplied notes, not treated as a fresh inspection.

| Reference | Supplied observations used | Not independently established |
| --- | --- | --- |
| InternPE | Reported badges without numbers; reported missing offer terms; matching email/website domain wording | Images, badge validity, verify-link behavior, original offer |
| Internship Studio | Course/project completion wording; reported missing compensation/contact details; stated dates | Employment versus training contract, actual compensation, accreditation |
| Oasis Infobyte | `.in` email versus `.com` website; reported badges and missing terms | Common domain ownership, registry records, original letter, similarity to another full letter |
| TCS | Supplied issuer/client phrase; reported entity-form and acceptance-name inconsistencies; stated salary | Actual issuer, authorized agency relationship, CIN match, recipient/signatory identities |
| Wipro | Defined role/date/probation; salary annexure reference; reported partial document | Annexures, full compensation, original page, recruitment authentication |

No original documents were supplied. No OCR, image/logo analysis, numerical similarity analysis, registry authentication, external reviews or model inference runs in this path. No company is labeled fraudulent, no payment demand is invented, and no reference is marked verified genuine. Full-letter numerical risk scores were omitted because their factual prerequisites cannot be checked from notes alone.

## UI and exports

Each report provides the supplied fields, exact matched phrases, quoted observations, positive indicators, evidence gaps, five issuer questions, verification links, a source-status table and an analysis-provenance panel. JSON exports preserve the same provenance. Compare references shows two cases side by side. Method & model explains both execution paths and the configured model.

The live adapter remains Groq with `openai/gpt-oss-20b`, whose weights are Apache-2.0 licensed. Reference results do not claim to use it. No recorded model run was supplied, so replay/recording and generic endpoint switching are not claimed or fabricated.

## Verification

The test suite validates all five records, exact URL mapping, lookalike rejection, multiple-phrase identity matching, ambiguous-input abstention, source quotations, provenance exports and the Streamlit URL/compare/model-card flow. Network access is prohibited throughout the offline tests.

To add a reference, provide actual source text and attributed notes, omit personal names and private contact details, and never create a quotation to fit a desired outcome. Re-run the tests before committing.
