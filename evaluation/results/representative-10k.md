# Retrieval evaluation

A relevant result is counted when the case's minimum number of hand-written theme terms appears in the top 5.
The impossible query has no relevance label and is inspected through its confidence.

| Query | Mode | Strategy | Top result | First relevant rank | Confidence | Exclusion violation |
|---|---|---|---|---:|---|---|
| något starkt med torsk och kokosmjölk | hybrid | search | Coconut Cod | 1 | medium | no |
| något starkt med torsk och kokosmjölk | lexical | search | Torsk | none | low | no |
| något starkt med torsk och kokosmjölk | semantic | search | Coconuts: Opening, Grating and Liquado | none | high | no |
| I have eggs, potatoes and onion | hybrid | search | Potato Bites | 1 | high | no |
| I have eggs, potatoes and onion | lexical | search | Grilled Potatoes and Onion | 1 | medium | no |
| I have eggs, potatoes and onion | semantic | search | Potato Bites | 1 | high | no |
| pasta con tomate y ajo | hybrid | search | Pasta with Scallops, Zucchini, and Tomatoes | 1 | high | no |
| pasta con tomate y ajo | lexical | search | BLT Pasta Salad | 1 | low | no |
| pasta con tomate y ajo | semantic | search | Pasta with Scallops, Zucchini, and Tomatoes | 1 | high | no |
| something quick and spicy with chicken | hybrid | search | Spicy Rapid Roast Chicken | 1 | high | no |
| something quick and spicy with chicken | lexical | search | Something Old and Something Blue | 2 | low | no |
| something quick and spicy with chicken | semantic | search | Classic Blasted Chicken | 2 | high | no |
| vegetarian comfort food | hybrid | search | Bea Arthur's Vegetarian Breakfast | 1 | medium | no |
| vegetarian comfort food | lexical | search | Vegetarian Gravy | 1 | low | no |
| vegetarian comfort food | semantic | search | Bea Arthur's Vegetarian Breakfast | 1 | medium | no |
| eggs, potatoes, onion | hybrid | search | Sweet Potato Potato Salad | 1 | high | no |
| eggs, potatoes, onion | lexical | search | Grilled Potatoes and Onion | 1 | high | no |
| eggs, potatoes, onion | semantic | search | Potato Bites | 1 | high | no |
| chikcen with garlick and chillies | hybrid | search | Garbanzo Bean Salad with Tomatoes and Chipotle Chilies | 2 | medium | no |
| chikcen with garlick and chillies | lexical | search | Tst | 2 | medium | no |
| chikcen with garlick and chillies | semantic | search | Cumin-Chipotle Ketchup | none | medium | no |
| lax med potatis och dill | hybrid | search | Potato Salmon Patties | 1 | high | no |
| lax med potatis och dill | lexical | search | Garlic Dill New Potatoes | 1 | low | no |
| lax med potatis och dill | semantic | search | Potato Salmon Patties | 1 | high | no |
| pollo con cebolla y ajo | hybrid | search | Pollo Borracho | 1 | medium | no |
| pollo con cebolla y ajo | lexical | search | Giant Prawns al Mojo de Ajo with Two Sauces | 2 | low | no |
| pollo con cebolla y ajo | semantic | search | Grilled Vegetables | 1 | high | no |
| blue unicorn foam with moon dust | hybrid | discovery | Christmas Croquembouche | n/a | low | no |
| blue unicorn foam with moon dust | lexical | discovery | Christmas Croquembouche | n/a | low | no |
| blue unicorn foam with moon dust | semantic | discovery | Christmas Croquembouche | n/a | low | no |
| something I haven't had before | hybrid | adventurous | Christmas Croquembouche | n/a | medium | no |
| something I haven't had before | lexical | adventurous | Christmas Croquembouche | n/a | medium | no |
| something I haven't had before | semantic | adventurous | Christmas Croquembouche | n/a | medium | no |
| överraska mig med något nytt | hybrid | adventurous | Christmas Croquembouche | n/a | medium | no |
| överraska mig med något nytt | lexical | adventurous | Christmas Croquembouche | n/a | medium | no |
| överraska mig med något nytt | semantic | adventurous | Christmas Croquembouche | n/a | medium | no |
| pasta con tomate sin ajo | hybrid | search | Greek Pasta with Tomatoes and White Beans | 1 | high | no |
| pasta con tomate sin ajo | lexical | search | BLT Pasta Salad | 1 | low | no |
| pasta con tomate sin ajo | semantic | search | Italian Pasta Salad I | 2 | high | no |

## Aggregate (labeled queries)

- **hybrid**: Hit@5 100%, MRR 0.950
  Exclusion violations: 0/2 evaluated rows
- **lexical**: Hit@5 90%, MRR 0.750
  Exclusion violations: 0/2 evaluated rows
- **semantic**: Hit@5 80%, MRR 0.700
  Exclusion violations: 0/2 evaluated rows
