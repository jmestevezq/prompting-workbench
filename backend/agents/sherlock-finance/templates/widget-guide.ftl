<#-- Widget usage guide for rendering UI components -->
### Widget Reference

<#list model.availableUiWidgetsList as w>
**${w.name}**
${w.description}

Example:
```json
${w.example}```

</#list>

### Widget Rules
- Use PIE_CHART for category breakdowns (e.g., spending by category).
- Use LINE_CHART for time-series data (e.g., monthly spending trends).
- Use TABLE for structured comparisons (max 4 columns, 8 rows).
- Always include a text summary alongside any widget.
- Never render a widget without sufficient data to populate it.
