# Contributing

CreditGuard AI follows the Spec-first workflow. Before changing code:

1. Read [SPEC/README.md](SPEC/README.md) and [SPEC-000 governance](SPEC/SPEC-000-project-governance.md).
2. Discuss the requirement and update the relevant Spec/FR/ADR.
3. Add acceptance criteria and a test case ID before implementation.
4. Keep changes scoped and use synthetic data in tests and screenshots.
5. Run the backend, frontend, security and contract checks that apply.
6. Record the result and evidence in the corresponding test case and Spec.

Do not commit `.env`, API keys, raw external responses, local database files, customer data or artifacts ignored by `.gitignore`.
