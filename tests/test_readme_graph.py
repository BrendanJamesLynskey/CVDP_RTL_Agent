"""The mermaid diagram in README.md must be the compiled graph. Regenerate it with
`PYTHONPATH=agent python -m cvdp_agent --mermaid` and paste it between the graph markers."""
import os
import re

from cvdp_agent.graph import mermaid

README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")


def test_readme_graph_matches_compiled_graph():
    text = open(README).read()
    m = re.search(r"<!-- graph:begin -->\s*```mermaid\n(.*?)```\s*<!-- graph:end -->", text, re.DOTALL)
    assert m, "README.md has no mermaid block between <!-- graph:begin --> and <!-- graph:end -->"
    assert m.group(1).strip() == mermaid().strip(), "README graph is stale: regenerate it (see this test's docstring)"
