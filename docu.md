# Référence du langage .exe

Cette page décrit uniquement les fonctionnalités réellement prévues par le parseur et le runtime actuels. Elle ne doit pas être interprétée comme une promesse de fonctions futures.

## Règles de syntaxe

- Les mots-clés, types et noms de fonctions sont en anglais.
- Toute instruction doit se terminer par `; ` sans l'espace final : le caractère `;` est obligatoire.
- Le retour à la ligne est facultatif après un point-virgule.
- Les blocs utilisent `{` et `}`. Les accolades des blocs ne sont pas suivies d'un point-virgule.
- Les appels natifs commencent toujours par `@`.
- La syntaxe historique (`let`, `send(...)` sans `@`, `v()`, `m()`, `R()`, `I()`, `E()`) est refusée.
- Le langage n'exécute pas de code Python arbitraire.

Exemple :

```text
var greeting.str = "Hello";
var count.int = 2;
set count = count + 1;
@send(f"{greeting}: {count}");
```

## Variables et expressions

Déclaration : `var name.type = value;`

Types acceptés par le parseur : `str`, `int`, `float`, `bool`, `list`, `dict`, `time`, `user.id`, `channel.id`, `category.id`, `role.id`, `message.id`.

Les déclarations typées vérifient actuellement que le nom de type est reconnu, mais **la vérification stricte de compatibilité entre type déclaré et valeur n'est pas complète**. Les suffixes `.id` servent à documenter l'intention et ne garantissent pas à eux seuls l'existence de l'objet Discord.

Pour mettre à jour une variable existante : `set name = expression;`

Les expressions sûres prennent en charge les constantes, variables, listes/tuples/dictionnaires littéraux, indexation, opérations arithmétiques (`+`, `-`, `*`, `/`, `//`, `%`), opérations booléennes (`and`, `or`, `not`) et comparaisons (`==`, `!=`, `<`, `<=`, `>`, `>=`). Les appels de fonctions arbitraires et l'accès aux attributs Python ne sont pas permis dans les expressions.

Valeurs booléennes : `True`, `False`; valeur vide : `None`. `randint(min, max)` est accepté comme expression bornée.

## Conditions et boucles

Les conditions actuellement prises en charge comparent une variable à une valeur :

```text
var mode.str = "safe";
if (mode == "safe") {
    @send("allowed");
} else {
    @send("blocked");
}
```

Les opérateurs de comparaison généraux existent dans les expressions, mais la syntaxe de bloc conditionnel ne prend pas encore en charge toutes les expressions composées. `elif` et les boucles sur des collections Discord ne sont pas pris en charge.

Répétition bornée :

```text
repeat(3) {
    @send("again");
}
```

Boucle numérique bornée :

```text
for i in range(0, 3) {
    @send(f"item {i}");
}
```

Les répétitions et plages sont limitées à 10 itérations et la profondeur d'imbrication est limitée. Le nombre d'actions compilées est vérifié avant exécution.

## Saisie

```text
var username.input{str, "What is your username?"} = "";
@send(f"Hello {username}!");
```

Le parseur accepte la déclaration de saisie pour les types compatibles. La réponse est demandée pendant l'exécution et est soumise au délai maximal configuré. La valeur initiale déclarée est actuellement ignorée.

## Fonctions natives actuellement reconnues

Toutes les fonctions natives doivent commencer par `@`.

| Fonction | Arguments acceptés par le parseur | Description |
|---|---|---|
| `@send(message)` | 1 argument | Envoie un message dans le contexte du script. |
| `@send(channel, message)` | 2 arguments | Envoie un message dans le salon indiqué si le runtime le prend en charge. |
| `@ban(user, reason?)` | 2 arguments actuellement | Bannit un membre. |
| `@unban(user_id)` | 1 à 2 arguments | Retire un bannissement. |
| `@kick(user, reason?)` | 1 à 2 arguments | Expulse un membre. |
| `@timeout(user, duration)` | 2 arguments | Applique un timeout ; durée exprimée en minutes dans le runtime actuel. |
| `@untimeout(user)` | 1 argument | Retire un timeout. |
| `@give_role(user, role)` / `@add_role(user, role)` | 2 arguments | Attribue un rôle. |
| `@remove_role(user, role)` | 2 arguments | Retire un rôle. |
| `@create_role(name, color?, permissions?)` | 1 à 3 arguments | Crée un rôle, selon les options prises en charge par le runtime. |
| `@delete_role(role_id)` | 1 argument | Supprime un rôle. |
| `@create_category(name, permissions?)` | 1 à 2 arguments | Crée une catégorie. |
| `@create_channel(name, permissions?, category?)` | 1 à 3 arguments | Crée un salon. |
| `@delete_channel(channel_id)` | 1 argument | Supprime un salon. |
| `@slowmode(seconds)` | 1 argument | Configure le mode lent dans le contexte pris en charge. |
| `@clear(count)` | 1 argument | Supprime un nombre limité de messages. |
| `@guilds_roles()` | aucun | Liste les rôles du serveur. |
| `@guilds_members()` | aucun | Liste jusqu'à 100 membres. |
| `@guilds_channels()` | aucun | Liste les salons du serveur. |
| `@guilds_categories()` | aucun | Liste les catégories du serveur. |

Les alias `@mute` et `@unmute` sont normalisés en `@timeout` et `@untimeout`. Les fonctions `@dm`, `@lock`, `@unlock`, les setters `@set_channel.*` et `@set_role.*`, `@time` et `@uptime` ne sont pas disponibles dans le runtime actuel. `@random(collection)` n'est pas une fonction native : utiliser `randint(min, max)` pour un entier aléatoire.

Le nombre d'arguments et les fonctions sont vérifiés par le parseur. Les actions Discord nécessitent également les permissions du membre et du bot, ainsi que le respect de la hiérarchie des rôles et des limites de l'API Discord.

## Limites et sécurité

- Taille maximale du script : 8 000 caractères.
- Budget d'actions configurable par `MAX_SCRIPT_ACTIONS` (20 par défaut).
- Durée maximale configurable par `SCRIPT_TIMEOUT_SECONDS` (60 secondes par défaut).
- Les actions de modération sont soumises à des vérifications de permissions côté bot.
- Les expressions sont évaluées à partir d'une liste autorisée de nœuds AST ; aucun `eval` ou `exec` n'est utilisé.
- Les fonctions et propriétés non listées ici doivent être considérées comme non prises en charge.
