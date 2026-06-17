# Graphify Setup

This project is configured with Graphify to create a knowledge graph of the codebase.

## Installation

Graphify has been installed globally and configured for this project:

1. Global CLI tool: `uv tool install graphifyy`
2. Project-specific Cursor integration: `graphify cursor install --project`
3. Git hooks for automatic updates: `graphify hook install`

## Usage

To rebuild the knowledge graph:
```
graphify .
```

To query the graph:
```
graphify query "What are the main components of this project?"
```

To find paths between components:
```
graphify path "ComponentA" "ComponentB"
```

## Configuration

- `.graphifyignore` - Specifies files and directories to exclude from the graph
- `.cursor/rules/graphify.mdc` - Cursor-specific rules for using the graph
- Git hooks automatically update the graph on commit/checkouts

## Output

Generated files are in `graphify-out/`:
- `graph.json` - The full graph data
- `manifest.json` - File timestamps for incremental updates
- `.graphify_analysis.json` - Extraction statistics
- Cache directory for intermediate processing

Note: Most files in `graphify-out/` should be committed to share the graph with the team, except for `manifest.json` and the cache directory.
