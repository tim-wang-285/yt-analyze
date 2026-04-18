# Workflow
- Keep a simple running change log under `changelog/` for meaningful script/pipeline changes.
- Use `uv` commands to run scripts and manage dependencies.
- Avoid unnecessary manual work when an existing or newly added package cleanly covers the need. Use `uv add` for adding missing packages. This will require user approval.
- Offer to commit to git. Commit messages should always be one-sentence.
# Output
- Speak brief and to the point. You're a programmer explaining to a programmer.
- When asking for approval - don't explain, just send the request.
- Don't report on steps in between, only explain at the very end when you finish a pass.
