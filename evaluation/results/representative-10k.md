# Retrieval evaluation

A relevant result is counted when the case's minimum number of hand-written theme terms appears in the top 5.
The impossible query has no relevance label and is inspected through its confidence.

| Query | Mode | Strategy | Top result | First relevant rank | Confidence | Exclusion violation |
|---|---|---|---|---:|---|---|
| något starkt med torsk och kokosmjölk | hybrid | search | Bouillabaise with Green Curry Paste Recipe | 1 | medium | no |
| något starkt med torsk och kokosmjölk | lexical | search | Shrimpcargot | none | low | no |
| något starkt med torsk och kokosmjölk | semantic | search | Homemade Ricotta Cheese Recipe | none | high | no |
| I have eggs, potatoes and onion | hybrid | search | Potato and Onion Latkes | 1 | high | no |
| I have eggs, potatoes and onion | lexical | search | Potato and Cheese Frittata | 1 | medium | no |
| I have eggs, potatoes and onion | semantic | search | Potato and Onion Latkes | 1 | high | no |
| pasta con tomate y ajo | hybrid | search | Delicious Pasta Bake | 1 | high | no |
| pasta con tomate y ajo | lexical | search | Pepper, tomato and basil pasta | 1 | low | no |
| pasta con tomate y ajo | semantic | search | Delicious Pasta Bake | 1 | high | no |
| something quick and spicy with chicken | hybrid | search | Darn Good Chicken | 2 | high | no |
| something quick and spicy with chicken | lexical | search | Boozy Blueberry Cherry Red Wine Pie | 2 | low | no |
| something quick and spicy with chicken | semantic | search | Darn Good Chicken | 3 | high | no |
| vegetarian comfort food | hybrid | search | Vegetarian Black Bean Pepper Soup | 1 | medium | no |
| vegetarian comfort food | lexical | search | Vegetarian McMuffin | 1 | low | no |
| vegetarian comfort food | semantic | search | Smokin' Cheese & Mac Bake Recipe | 4 | high | no |
| eggs, potatoes, onion | hybrid | search | Potato and Onion Latkes | 1 | high | no |
| eggs, potatoes, onion | lexical | search | Crisp baked potatoes | 2 | medium | no |
| eggs, potatoes, onion | semantic | search | Potato and Onion Latkes | 1 | high | no |
| chikcen with garlick and chillies | hybrid | search | Chilaquiles with Salsa Verde | 1 | medium | no |
| chikcen with garlick and chillies | lexical | discovery | Golden Syrup Cake | 2 | low | no |
| chikcen with garlick and chillies | semantic | search | Chicken Tortilla Chowder | 3 | high | no |
| lax med potatis och dill | hybrid | search | Citrus salmon with herb & caper crushed potatoes | 1 | medium | no |
| lax med potatis och dill | lexical | search | Black-Eyed Peas and Dill Potato Skillet | 1 | low | no |
| lax med potatis och dill | semantic | search | Citrus salmon with herb & caper crushed potatoes | 1 | high | no |
| pollo con cebolla y ajo | hybrid | search | Red pepper and onion casserole with garlic and coriander mushrooms | 1 | high | no |
| pollo con cebolla y ajo | lexical | search | Arroz Con Pollo | none | low | no |
| pollo con cebolla y ajo | semantic | search | Red pepper and onion casserole with garlic and coriander mushrooms | 1 | high | no |
| blue unicorn foam with moon dust | hybrid | discovery | Golden Syrup Cake | n/a | low | no |
| blue unicorn foam with moon dust | lexical | discovery | Golden Syrup Cake | n/a | low | no |
| blue unicorn foam with moon dust | semantic | discovery | Golden Syrup Cake | n/a | low | no |
| something I haven't had before | hybrid | adventurous | Golden Syrup Cake | n/a | medium | no |
| something I haven't had before | lexical | adventurous | Golden Syrup Cake | n/a | medium | no |
| something I haven't had before | semantic | adventurous | Golden Syrup Cake | n/a | medium | no |
| överraska mig med något nytt | hybrid | adventurous | Golden Syrup Cake | n/a | medium | no |
| överraska mig med något nytt | lexical | adventurous | Golden Syrup Cake | n/a | medium | no |
| överraska mig med något nytt | semantic | adventurous | Golden Syrup Cake | n/a | medium | no |
| pasta con tomate sin ajo | hybrid | search | Pasta Chicken and Sun-Dried Tomatoes | 1 | high | no |
| pasta con tomate sin ajo | lexical | search | Green Tomato Pasta Toss | 1 | low | no |
| pasta con tomate sin ajo | semantic | search | Sundried Tomato Pasta Salad | 1 | high | no |

## Aggregate (labeled queries)

- **hybrid**: Hit@5 100%, MRR 0.950
  Exclusion violations: 0/2 evaluated rows
- **lexical**: Hit@5 80%, MRR 0.650
  Exclusion violations: 0/2 evaluated rows
- **semantic**: Hit@5 90%, MRR 0.692
  Exclusion violations: 0/2 evaluated rows
