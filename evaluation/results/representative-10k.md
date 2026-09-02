# Retrieval evaluation

A relevant result is counted when the case's minimum number of hand-written theme terms appears in the top 5.
The impossible query has no relevance label and is inspected through its confidence.

| Query | Mode | Strategy | Top result | First relevant rank | Confidence | Exclusion violation |
|---|---|---|---|---:|---|---|
| något starkt med torsk och kokosmjölk | hybrid | search | Coconut Fish Curry | 1 | medium | no |
| något starkt med torsk och kokosmjölk | lexical | search | Torsk | none | low | no |
| något starkt med torsk och kokosmjölk | semantic | search | Rick's Caribbean Ropa Vieja | none | high | no |
| I have eggs, potatoes and onion | hybrid | search | Apple Potato Pancakes | 1 | medium | no |
| I have eggs, potatoes and onion | lexical | search | Potato Onion Loaf | 1 | medium | no |
| I have eggs, potatoes and onion | semantic | search | Egg Foo Young | 1 | high | no |
| pasta con tomate y ajo | hybrid | search | Penne Pasta with Spinach and Bacon | 1 | high | no |
| pasta con tomate y ajo | lexical | search | Mojo de Ajo | 2 | medium | no |
| pasta con tomate y ajo | semantic | search | Tomato-Cream Sauce for Pasta | 1 | high | no |
| something quick and spicy with chicken | hybrid | search | Spicy Honey-Roasted Chicken | 1 | high | no |
| something quick and spicy with chicken | lexical | search | Chicken Something | 4 | medium | no |
| something quick and spicy with chicken | semantic | search | Spicy Honey-Roasted Chicken | 1 | high | no |
| vegetarian comfort food | hybrid | search | Vegetarian Pate | 1 | medium | no |
| vegetarian comfort food | lexical | search | Northern Comfort | 2 | low | no |
| vegetarian comfort food | semantic | search | Vegan Stew | 3 | medium | no |
| eggs, potatoes, onion | hybrid | search | Rub Noodle Potato Soup | 1 | high | no |
| eggs, potatoes, onion | lexical | search | Potato Onion Loaf | 1 | medium | no |
| eggs, potatoes, onion | semantic | search | Garlic Pickled Eggs | 1 | high | no |
| chikcen with garlick and chillies | hybrid | search | Chilled Russian Salad Dressing | 3 | medium | no |
| chikcen with garlick and chillies | lexical | discovery | Custom-Made Ice Cream Sandwich | 3 | low | no |
| chikcen with garlick and chillies | semantic | search | Zucchini Chive Dip | none | high | no |
| lax med potatis och dill | hybrid | search | Potato Salmon Patties | 1 | high | no |
| lax med potatis och dill | lexical | search | Dill Sour Cream Potato Salad | 1 | low | no |
| lax med potatis och dill | semantic | search | Fat Tuesday Salmon | 1 | high | no |
| pollo con cebolla y ajo | hybrid | search | Roasted Rosemary Chicken And Vegetables | 1 | medium | no |
| pollo con cebolla y ajo | lexical | search | Mojo de Ajo | 3 | low | no |
| pollo con cebolla y ajo | semantic | search | Brown Bag Chicken | 1 | high | no |
| blue unicorn foam with moon dust | hybrid | discovery | Custom-Made Ice Cream Sandwich | n/a | low | no |
| blue unicorn foam with moon dust | lexical | discovery | Custom-Made Ice Cream Sandwich | n/a | low | no |
| blue unicorn foam with moon dust | semantic | discovery | Custom-Made Ice Cream Sandwich | n/a | low | no |
| something I haven't had before | hybrid | adventurous | Custom-Made Ice Cream Sandwich | n/a | medium | no |
| something I haven't had before | lexical | adventurous | Custom-Made Ice Cream Sandwich | n/a | medium | no |
| something I haven't had before | semantic | adventurous | Custom-Made Ice Cream Sandwich | n/a | medium | no |
| överraska mig med något nytt | hybrid | adventurous | Custom-Made Ice Cream Sandwich | n/a | medium | no |
| överraska mig med något nytt | lexical | adventurous | Custom-Made Ice Cream Sandwich | n/a | medium | no |
| överraska mig med något nytt | semantic | adventurous | Custom-Made Ice Cream Sandwich | n/a | medium | no |
| pasta con tomate sin ajo | hybrid | search | Mediterranean Pasta | 1 | high | no |
| pasta con tomate sin ajo | lexical | search | Tomato and Bacon Pasta Bake | 1 | low | no |
| pasta con tomate sin ajo | semantic | search | Classic Italian Pasta Salad | 1 | high | no |

## Aggregate (labeled queries)

- **hybrid**: Hit@5 100%, MRR 0.933
  Exclusion violations: 0/2 evaluated rows
- **lexical**: Hit@5 90%, MRR 0.592
  Exclusion violations: 0/2 evaluated rows
- **semantic**: Hit@5 80%, MRR 0.733
  Exclusion violations: 0/2 evaluated rows
