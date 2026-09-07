# CRQ V1 frontend

This React/TypeScript workspace implements the governed Phase 4B product experience. It imports the canonical contracts and approved IT Financial Services / OT Power Generation examples from the repository root. It contains no quantitative calculations.

## Local use

```bash
npm install
npm run dev
npm test
npm run build
```

The default is `demo` mode. Set `VITE_CRQ_DATA_MODE=api` and `VITE_CRQ_API_BASE_URL` to use the three-route Phase 4A asynchronous API. The same pages and components are used in either mode.

## Boundaries

- `src/contracts`: contract-aligned types and governed repository data
- `src/api`: replaceable demo and HTTP run adapters
- `src/features/assessment`: input ownership, workflow and field expansion
- `src/features/results`: canonical result presentation
- `src/pages`: route-level screens
- `src/styles`: design tokens, responsive layout and reduced-motion behavior

Login and AI interpretation are placeholders. No Cognito, persistence, LLM, AWS infrastructure or engine behavior is implemented here.
