# Research notes and decisions

Last verified: 2026-09-02.

## Retrieval

- Sentence Transformers documents `paraphrase-multilingual-MiniLM-L12-v2` as a model trained on
  parallel data for 50+ languages. FastEmbed provides a quantized ONNX build, avoiding the much
  larger PyTorch runtime: https://sbert.net/docs/sentence_transformer/pretrained_models.html and
  https://qdrant.github.io/fastembed/
- OMAI's supplied archive contains 173,278 JSON Lines records from 33 publishers. Inspection found
  descriptions on about 91% of records, image URLs on about 91%, and timing data on about 77%:
  https://github.com/OMAI-dev/arbetsprov-recept
- The Docker profile uses deterministic reservoir sampling to select 10,000 recipes across the
  full source-ordered stream. A vector database is unnecessary at that serving size. A normalized
  NumPy matrix and sparse TF-IDF matrix keep the complete retrieval path local and inspectable. A
  future move to an ANN index changes candidate retrieval, not the API or scoring contract.
- Maximal Marginal Relevance established a simple tradeoff between relevance and non-redundancy.
  The discovery path uses the same idea in a smaller form by penalizing ingredient and category
  repetition after corpus-relative distinctiveness scoring:
  https://aclanthology.org/X98-1025/

## Azure AI

- Microsoft lists `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol` with Responses API and
  structured-output support. Some subscriptions require a quota request:
  https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure
- GPT-5.6 supports low reasoning effort. Query extraction does not justify pro mode or a larger
  family member: https://learn.microsoft.com/azure/foundry/openai/how-to/reasoning
- The v1 Responses API accepts API-key or Microsoft Entra authentication; Microsoft recommends
  Entra: https://learn.microsoft.com/azure/foundry/openai/how-to/responses
- An Azure-hosted app should use managed identity and receive the `Cognitive Services OpenAI User`
  role. The application then stores no cloud credential:
  https://learn.microsoft.com/azure/foundry-classic/openai/how-to/managed-identity
- Current Microsoft examples pass the bearer-token provider callable to the OpenAI client so tokens
  can refresh, rather than resolving one token at startup:
  https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview

The LLM receives only the user's short query. It is asked for strict structured constraints and is
never given the recipe dataset. `store=false`, a short timeout, no retries, rate limiting, and a
deterministic fallback bound privacy, cost, and availability risk.

## Security and accessibility

- OWASP API4:2023 recommends bounding payload sizes, records returned, request frequency, execution
  resources, and third-party spending. This app bounds raw request bodies, validated fields, result
  count, local concurrency, and optional AI calls:
  https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/
- Strict structured output, no tools, small input and output limits, and deterministic validation
  reduce the optional LLM attack surface. Prompt injection remains a reason not to give this
  extractor tools, secrets, or authority:
  https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- W3C's dialog pattern recommends focus inside a modal and restoration to its invoker. The native
  dialogs follow that behavior and focus their headings when opened:
  https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- The decorative food motion runs once and honors `prefers-reduced-motion`, following W3C guidance
  for nonessential animation:
  https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions

## Open source and deployment

- GitHub Actions can use OIDC to Azure without a long-lived Azure deployment secret:
  https://docs.github.com/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure
- GitHub Pages publishes the dependency-free frontend, while Railway runs the same Docker image
  available through GHCR. Runtime configuration remains server-side:
  https://docs.github.com/pages and https://docs.railway.com/guides/services
- Docker warns that build arguments and image environment variables are not a safe way to pass
  secrets. This project needs no build-time secret; AI credentials are runtime-only:
  https://docs.docker.com/build/building/secrets/

## Alternatives considered

| Decision | Chosen | Credible alternative | Why not now | Revisit when |
|---|---|---|---|---|
| Semantic runtime | FastEmbed ONNX | Sentence Transformers/PyTorch | Larger image and memory footprint | GPU inference or model fine-tuning is required |
| Vector search | NumPy cosine | Qdrant/pgvector/FAISS | Extra service or native complexity for the 10k serving profile | Millions of recipes or strict latency SLOs |
| Query understanding | Optional GPT-5.6 Luna | Always translate/parse with an LLM | Adds cost, latency, and a hard dependency | Measured evaluation shows consistent material gain |
| Lexical search | Character TF-IDF | BM25/Elasticsearch | Current approach handles typos with one local dependency | Field weighting or operational search tooling is needed |
| Frontend | Vanilla static files | React/Next.js | Build system and state layer add no assignment value | Product scope grows beyond a search demo |
