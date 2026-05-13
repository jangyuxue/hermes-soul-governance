# Workflows

<!-- 
  This directory stores your personal workflows and procedures.
  Each workflow is a separate .md file.
  
  The agent will auto-create files here when you say things like:
  - "My steps for deploying are..."
  - "First I do X, then Y..."
  - "The process is..."
  - "I usually do..."
  
  Naming convention: <workflow-name>.md (lowercase, hyphens)
  Example: deploy-to-production.md, code-review.md, morning-routine.md
-->

## Example Workflow

Create a file like `my-deploy-workflow.md`:

```markdown
# Deploy to Production

## Steps

1. Run tests locally: `pytest tests/`
2. Push to main: `git push origin main`
3. Wait for CI to pass
4. Tag release: `git tag v1.0.0 && git push --tags`
5. Deploy via: `make deploy ENV=production`

## Notes

- Always check with team before deploying on Friday
- If tests fail, check database migrations first
```
