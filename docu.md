# Documentation du langage .exe

Langage de scripts personnalisé pour automatiser des actions sur Discord avec le bot. Ce n'est pas Python : seuls les éléments documentés ici sont disponibles.

## Principes et sécurité

- Seuls les utilisateurs dont l'identifiant Discord est dans la whitelist peuvent lancer un script.
- Aucun Python arbitraire : pas de `eval`, pas de `exec`, pas de fonctions définies par l'utilisateur et pas d'accès libre aux modules.
- Les fonctions natives sont explicitement autorisées par le bot.
- Les permissions Discord et la hiérarchie des rôles restent obligatoires : la whitelist ne les contourne pas.
- Le script est analysé et vérifié avant l'exécution. Des erreurs Discord peuvent cependant survenir au moment d'exécuter une action.

## Syntaxe générale

Les blocs utilisent `{}`. Les retours à la ligne et l'indentation sont facultatifs. Le point-virgule `;` sépare les instructions.

```text
var nom.str = "Tests"; var nombre.int = 3; @send(f"{nom} : {nombre}");
```

Les fonctions natives commencent par `@`. Aucun commentaire n'est accepté. `#` est l'opérateur logique NOT ; dans une chaîne, il peut servir de caractère normal, par exemple `"#FF0000"`.

## Types et variables

Chaque variable doit déclarer son type :

| Type | Signification |
|---|---|
| `str` | Texte |
| `int` | Entier |
| `float` | Décimal |
| `bool` | `True` ou `False` |
| `user.id` | Identifiant utilisateur |
| `chanel.id` | Identifiant de salon |
| `categorie.id` | Identifiant de catégorie |
| `role.id` | Identifiant de rôle |
| `message.id` | Identifiant de message |
| `list` | Liste |
| `dict` | Dictionnaire |
| `time` | Durée |

Les noms `chanel` et `categorie` sont volontairement orthographiés ainsi dans le langage.

```text
var pseudo.str = "Alex"
var essais.int = 3
var ratio.float = 1.5
var actif.bool = True
var cible.user.id = ""
var salons.list = ()
var configuration.dict = []
var attente.time = 10
set essais = 4
```

`""` signifie vide/non renseigné lors de l'initialisation, y compris pour les types autres que `str`. Une liste vide s'écrit `()`, un dictionnaire vide `[]`. `set nom = valeur` modifie une variable existante, sans répéter son type ; une valeur incompatible produit une erreur de type.

## Opérateurs et expressions

Arithmétique : `+`, `-`, `*`, `/`, `%`.

Comparaison : `==`, `!=`, `<`, `>`, `<=`, `>=`. Les types comparés doivent être compatibles.

Logique : `&&` signifie ET, `!!` signifie OU et `#` signifie NON. Les parenthèses regroupent les expressions. Les priorités suivent les règles usuelles des expressions.

## Conditions

```text
if (essais >= 3 && actif == True) {
    @send("Conditions remplies");
} elif (essais > 0) {
    @send("Encore des essais");
} else {
    @send("Aucun essai restant");
}
```

`elif` et `else if` sont acceptés. La condition doit produire un booléen.

## Boucles

```text
repeat(3) {
    @send("Répétition");
}

for membre in guild.user {
    @send(membre.name);
}

for i in range(0, 5) {
    @send(f"Tour {i}");
}
```

`repeat(n)` répète le bloc n fois. `for variable in collection` parcourt une collection. `range(debut, fin)` inclut le début et exclut la fin : `range(0, 5)` produit 0 à 4. Les collections Discord doivent être parcourues sur un instantané stable si le script les modifie.

## Chaînes formatées

```text
var pseudo.str = "Alex"
var score.int = 12
@send(f"Joueur : {pseudo}, score : {score}");
@send(f"Prochain score : {score + 1}");
```

Les expressions valides dans `f"..." ` sont évaluées. Si une portion entre accolades ne peut pas être analysée comme expression, elle est conservée telle quelle dans le texte.

## Listes et dictionnaires

Les listes utilisent des parenthèses, les positions commencent à zéro :

```text
var nombres.list = (10, 20, 30)
add nombres.list = {1, 15}
set nombres.list = {0, 5}
del nombres.list = 2
```

- `add liste = {position, valeur}` insère une valeur.
- `set liste = {position, valeur}` remplace un élément.
- `del liste = position` supprime un élément.

Les dictionnaires utilisent des crochets et des paires clé/valeur :

```text
var config.dict = ["mode": "test", "active": True]
add config.dict = {"langue", "fr"}
set config.dict.value = {"mode", "production"}
set config.dict.key = {"langue", "locale"}
del config.dict = "active"
```

Les clés/positions doivent être valides. Un renommage de clé ne doit pas écraser une clé existante.
