TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "record_entries",
            "description": (
                "Record one or more purchases or sales the trader mentioned. "
                "Use one item per product, except explicitly separate transactions. "
                "Resolve repeated spoken prices and explicit corrections before recording. "
                "A price repeated for emphasis in one transaction is counted once; "
                "never concatenate or sum repeated mentions. Ask for clarification "
                "without calling this tool when the intended amount is ambiguous."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["purchase", "sale"]},
                                "product_name": {
                                    "type": "string",
                                    "description": "Core item name, e.g. 'rice', not 'bags of rice'",
                                },
                                "total_amount": {
                                    "type": "number",
                                    "description": (
                                        "TOTAL naira for this line (quantity x unit price if given per unit). "
                                        "Count a price repeated for emphasis only once. Use the explicitly "
                                        "corrected price, and never concatenate repeated figures."
                                    ),
                                },
                                "quantity": {"type": ["number", "null"]},
                                "unit": {
                                    "type": ["string", "null"],
                                    "description": "bag, basket, derica, crate, kg...",
                                },
                                "occurred_on": {
                                    "type": ["string", "null"],
                                    "description": "YYYY-MM-DD, only if the trader mentioned a day. Otherwise null.",
                                },
                            },
                            "required": ["action", "product_name", "total_amount"],
                        },
                    }
                },
                "required": ["entries"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_summary",
            "description": "Get total sales and purchases for a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
                    "date_to": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
                },
                "required": [],
            },
        },
    },
]
