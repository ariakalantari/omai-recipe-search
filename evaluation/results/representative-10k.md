# Retrieval evaluation

A relevant result is counted when the case's minimum number of hand-written theme terms appears in the top 5.
The impossible query has no relevance label and is inspected through its confidence.

| Query | Mode | Top result | First relevant rank | Confidence |
|---|---|---|---:|---|
| något starkt med torsk och kokosmjölk | hybrid | Coconut Rice | n/a | medium |
| något starkt med torsk och kokosmjölk | lexical | Torsk | n/a | low |
| något starkt med torsk och kokosmjölk | semantic | Coconut Rice | n/a | high |
| I have eggs, potatoes and onion | hybrid | Irish Eggs | 1 | medium |
| I have eggs, potatoes and onion | lexical | Grilled Potatoes and Onion | 1 | medium |
| I have eggs, potatoes and onion | semantic | Irish Eggs | 1 | high |
| pasta con tomate y ajo | hybrid | Pasta with Scallops, Zucchini, and Tomatoes | 1 | medium |
| pasta con tomate y ajo | lexical | Tomato and Garlic Pasta | 1 | low |
| pasta con tomate y ajo | semantic | Pasta with Scallops, Zucchini, and Tomatoes | 1 | high |
| something quick and spicy with chicken | hybrid | Spicy Rapid Roast Chicken | 1 | high |
| something quick and spicy with chicken | lexical | Chicken Something | 2 | medium |
| something quick and spicy with chicken | semantic | Spicy Rapid Roast Chicken | 1 | high |
| vegetarian comfort food | hybrid | Vegetarian Meatloaf with Vegetables | 1 | medium |
| vegetarian comfort food | lexical | Vegetarian Meatloaf with Vegetables | 1 | low |
| vegetarian comfort food | semantic | Vegetarian Meatloaf with Vegetables | 1 | medium |
| eggs, potatoes, onion | hybrid | Irish Eggs | 1 | high |
| eggs, potatoes, onion | lexical | Grilled Potatoes and Onion | 1 | high |
| eggs, potatoes, onion | semantic | Irish Eggs | 1 | high |
| chikcen with garlick and chillies | hybrid | Chicken Chimichangas with Sour Cream Sauce | 1 | medium |
| chikcen with garlick and chillies | lexical | Pork Chile Rojo (Pulled Pork with Red Chile Sauce) | 2 | low |
| chikcen with garlick and chillies | semantic | Easy Spicy Mexican-American Chicken | 2 | medium |
| lax med potatis och dill | hybrid | Potato Salmon Patties | 1 | medium |
| lax med potatis och dill | lexical | Garlic Dill New Potatoes | 1 | medium |
| lax med potatis och dill | semantic | Potato Salmon Patties | 1 | high |
| pollo con cebolla y ajo | hybrid | Onion Chicken in Balsamic Sauce | 1 | medium |
| pollo con cebolla y ajo | lexical | Carol's Arroz Con Pollo | 1 | low |
| pollo con cebolla y ajo | semantic | Onion Chicken in Balsamic Sauce | 1 | high |
| blue unicorn foam with moon dust | hybrid | Aunt Blanche's Blueberry Muffins | n/a | low |
| blue unicorn foam with moon dust | lexical | Pork Chops with Blue Cheese Gravy | n/a | low |
| blue unicorn foam with moon dust | semantic | Glorious Sponge Cake | n/a | medium |

## Aggregate (labeled queries)

- **hybrid**: Hit@5 100%, MRR 1.000
- **lexical**: Hit@5 100%, MRR 0.875
- **semantic**: Hit@5 100%, MRR 0.938
