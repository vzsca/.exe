# Documentation du langage .exe

Langage de scripts personnalisé pour automatiser des actions sur Discord avec le bot. Ce n'est pas Python : seuls les éléments documentés ici sont disponibles.

## Conventions internationales

La syntaxe du langage utilise des noms anglais : `member`, `channel`, `category`, `role`, `message`, ainsi que des fonctions comme `create_channel`, `delete_channel`, `set_channel` et `add_role`. Les textes affichés par les scripts peuvent être dans la langue choisie par leur auteur. Les identifiants de langage restent anglais pour assurer une syntaxe stable entre les traductions de la documentation.

## Principes et sécurité

- Seuls les users dont l'identifiant Discord est dans la whitelist peuvent lancer un script.
- Aucun Python arbitraire : pas de `eval`, pas de `exec`, pas de fonctions définies par l'user et pas d'accès libre aux modules.
- Les fonctions natives sont explicitement autorisées par le bot.
- Les permissions Discord et la hiérarchie des rôles restent obligatoires : la whitelist ne les contourne pas.
- Le script est analysé et vérifié avant l'exécution. Des erreurs Discord peuvent cependant survenir au moment d'exécuter une action.

## Syntaxe générale

Les blocs utilisent `{}`. **Chaque instruction doit se terminer par `;`**. Le retour à la ligne est facultatif après ce séparateur : plusieurs instructions peuvent donc être écrites sur une même ligne. Les en-têtes de blocs (`if (...) {`, `repeat(...) {`, etc.) et les accolades fermantes `}` ne prennent pas de `;` à eux seuls. Les anciennes syntaxes compactes et les appels sans `@` ne font pas partie du langage.

```text
var name.str = "Tests"; var count.int = 3; @send(f"{name}: {count}");
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
| `user.id` | Identifiant user |
| `channel.id` | Identifiant de channel |
| `category.id` | Identifiant de category |
| `role.id` | Identifiant de rôle |
| `message.id` | Identifiant de message |
| `list` | Liste |
| `dict` | Dictionnaire |
| `time` | Durée |

Convention internationale : les mots-clés, noms de types, collections, propriétés et fonctions du langage utilisent l'anglais. Les noms français ne sont utilisés que dans les explications de cette documentation ou dans les textes écrits par l'auteur du script.

```text
var username.str = "Alex";
var attempts.int = 3;
var ratio.float = 1.5;
var enabled.bool = True;
var target.user.id = None;
var channels.list = ();
var configuration.dict = [];
var wait.time = 10;
set attempts = 4;
```

`None` signifie qu’aucune valeur n’est définie. Il peut initialiser une variable typée en attente d’une valeur, notamment un identifiant Discord. `""` reste une chaîne vide de type `str`. Une liste vide s'écrit `()`, un dictionnaire vide `[]`. `set nom = valeur` modifie une variable existante, sans répéter son type. Le moteur actuel vérifie certaines valeurs lors de la compilation, mais la validation stricte de tous les types déclarés reste incomplète.

## Opérateurs et expressions

Arithmétique : `+`, `-`, `*`, `/`, `%`.

Comparisons : `==`, `!=`, `<`, `>`, `<=`, `>=`. Les types comparés doivent être compatibles.

Logique : `&&` signifie ET, `!!` signifie OU et `#` signifie NON. Les parenthèses regroupent les expressions. Les priorités suivent les règles usuelles des expressions.

## Conditions

```text
if (attempts >= 3 && enabled == True) {
    @send("Conditions met");
} elif (attempts > 0) {
    @send("More attempts");
} else {
    @send("No attempts remaining");
}
```

`elif` et `else if` sont acceptés. La condition doit produire un booléen.

## Boucles

```text
repeat(3) {
    @send("Repeat");
}

for member in guild.member {
    @send(member.name);
}

for i in range(0, 5) {
    @send(f"Tour {i}");
}
```

`repeat(n)` repeats the block n times. `for variable in collection` iterates over a collection. `range(start, stop)` includes the start and excludes the stop: `range(0, 5)` produces 0 to 4. Discord collections should be iterated over a stable snapshot if the script modifies them.

## Chaînes formatées

```text
var username.str = "Alex";
var score.int = 12;
@send(f"Player: {username}, score: {score}");
@send(f"Prochain score: {score + 1}");
```

Les expressions valides dans une chaîne `f"…"` sont évaluées. Si une portion entre accolades ne peut pas être analysée comme expression, elle est conservée telle quelle dans le texte.

## Listes et dictionnaires

Les listes utilisent des parenthèses, les positions commencent à zéro :

```text
var numbers.list = (10, 20, 30);
add numbers.list = (1, 15);
set numbers.list = (0, 5);
del numbers.list = 2;
```

- `add list = (position, value)` inserts a value.
- `set list = (position, value)` replaces an element.
- `del list = position` deletes an element.

Les dictionnaires utilisent des crochets et des paires clé/valeur :

```text
var config.dict = ["mode": "test", "active": True];
add config.dict = ("language", "en");
set config.dict.value = ("mode", "production");
set config.dict.key = ("language", "locale");
del config.dict = "active";
```

Dictionary deletion is performed by key only, never by position. Keys and positions must be valid. Renaming a key must not overwrite an existing key.

## Entrées user

Une entrée est déclarée avec `.input` suivi du type attendu et de la question. `input` est un modificateur de déclaration, pas un type.

```text
var username.input{str, "What is your username?"} = "";
var age.input{int, "How old are you?"} = "";
var enabled.input{bool, "Enable this feature?"} = False;
var target.input{user.id, "What is the Discord ID?"} = None;
```

Types pris en charge par les entrées : `str`, `int`, `float`, `bool`, `user.id`, `channel.id`, `category.id`, `role.id` et `message.id`. Les entrées de type liste et dictionnaire ne sont pas prises en charge.

Fonctionnement prévu :

1. Le bot envoie la question dans le channel où le script a été lancé.
2. Il attend la prochaine réponse de la personne qui a lancé le script.
3. La réponse est convertie et validée selon le type attendu.
4. Le délai d'attente est d'une minute.
5. En cas de réponse invalide ou de délai dépassé, le script s'arrête. Il n'y a pas de seconde tentative dans la même exécution : il faut relancer le script.

For boolean input, accepted answers are `true`/`false`, `yes`/`no`, `oui`/`non`, and `1`/`0` (case-insensitive). They are converted to `True` or `False`.

## Objets et collections Discord

### Collections

- `guild.member` : members du serveur.
- `guild.channel` : channels du serveur.
- `guild.role` : rôles du serveur.

Without a property, a collection or object defaults to its identifier. Une propriété explicite permet d'accéder à une autre donnée.

### Propriétés

| Objet | Propriétés prévues |
|---|---|
| Utilisateur/member | `.id`, `.name`, `.display_name`, `.bot`, `.role` |
| Salon (`channel`) | `.id`, `.name`, `.category`, `.permissions`, `.slowmode`, `.type` |
| Catégorie | `.id`, `.name`, `.permissions` |
| Rôle | `.id`, `.name`, `.color`, `.permissions`, `.position`, `.managed` |
| Message | `.id`, `.content`, `.author`, `.channel` |

La disponibilité exacte d'une propriété doit être vérifiée dans l'implémentation du bot et dépend de l'objet Discord. Le langage ne donne pas accès à des attributs Python arbitraires.

```text
for role in guild.role {
    if (role.name == "Old role") {
        @delete_role(role.id, "Cleanup");
    }
}

if ("Moderator" in guild.role.name) {
    @send("Le rôle Moderator existe");
}
```

Le test `valeur in collection.propriete` vérifie si la valeur figure parmi les valeurs de cette propriété. Dans une boucle, `role.name` désigne le nom du rôle parcouru.

## Fonctions natives

Tous les appels de fonctions commencent par `@`. La syntaxe est obligatoire même si le moteur convertit ensuite les appels en instructions internes. Seules les fonctions effectivement présentes dans le parseur et le runtime sont utilisables ; certaines fonctions de configuration listées ci-dessous restent prévues et ne sont pas encore implémentées.

### Valeurs et informations

| Fonction | Rôle |
|---|---|
| `@random(collection)` | Choisit un élément au hasard dans une liste ou une collection fournie. Pour un dictionnaire, le comportement prévu est de renvoyer une valeur. |
| `@randint(min, max)` | Renvoie un entier aléatoire entre les bornes incluses. |
| `@time` | Donne l'heure actuelle. |
| `@uptime` | Donne la durée écoulée depuis le démarrage du bot. |

### Modération

| Fonction | Paramètres | Résultat attendu |
|---|---|---|
| `@ban(user, reason?)` | Utilisateur, reason facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@kick(user, reason?)` | Utilisateur, reason facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@unban(user_id)` | Identifiant user uniquement | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@mute(user, duration, reason?)` | Utilisateur, durée, reason facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@unmute(user, reason?)` | Utilisateur, reason facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |

### Channels and categories

| Fonction | Rôle |
|---|---|
| `@create_channel(name, permissions?, category?)` | Crée un channel et doit renvoyer son identifiant `channel.id` en cas de succès. |
| `@delete_channel(id, reason?)` | Supprime un channel. |
| `@set_channel.name(channel_id, name)` | Modifie le nom d'un channel. |
| `@set_channel.permissions(channel_id, permission:True;other_permission:False)` | Modifie une ou plusieurs permissions du channel. |
| `@slowmode(channel, seconds)` | Configure le mode lent du channel. |
| `@lock(channel)` | Verrouille le channel selon les permissions Discord. |
| `@unlock(channel)` | Retire le verrouillage appliqué par le bot. |

### Rôles

| Fonction | Rôle |
|---|---|
| `@create_role(name, color?, permissions?)` | Crée un rôle et doit renvoyer son identifiant `role.id` en cas de succès. |
| `@delete_role(id, reason?)` | Supprime un rôle. |
| `@set_role.name(role_id, name)` | Modifie le nom d'un rôle. |
| `@set_role.color(role_id, "#RRGGBB")` | Modifie la color d'un rôle. |
| `@set_role.permissions(role_id, permission:True;other_permission:False)` | Modifie une ou plusieurs permissions du rôle. |
| `@add_role(user, role)` | Attribue un rôle à un user. |

For `.permissions`, each permission is set to `True` or `False`. Multiple changes are separated by semicolons. Permission names must match the Discord permissions supported by the bot.

### Messages

| Fonction | Rôle |
|---|---|
| `@send(message)` | Envoie un message dans le channel où le script a été lancé. |
| `@send(channel, message)` | Envoie un message dans le channel indiqué. |
| `@dm(user, message)` | Envoie un message privé à l'user. |
| `@clear(count)` | Supprime le nombre de messages indiqué, dans les limites imposées par Discord. |

Messages can be plain or formatted strings: `@send(f"Welcome {member.name} !")`.

## Durées

The `time` type represents a duration. Without a suffix, the value is in minutes.

| Suffixe | Unité |
|---|---|
| none | minutes |
| `s`, `sec` | seconds |
| `m`, `min` | minutes |
| `h` | hours |
| `d` | days |

Suffixes are case-insensitive.

```text
var short.time = 30sec;
var standard.time = 10;
var long.time = 2h;
@mute(target, standard, "Spam");
```

Ici, `standard` vaut dix minutes. Les durées doivent être valides et positives pour les actions qui exigent une durée.

## Résultats et erreurs

Les fonctions de modération et les fonctions de modification/suppression Discord doivent renvoyer `True` en cas de succès. En cas d'échec, elles renvoient `False` et indiquent le nom de la fonction ainsi qu'un message explicatif.

Un résultat `False` correspond à un échec à l'exécution, pas à une erreur de syntaxe. Une action peut échouer même si le script a été correctement compilé.

## Erreurs et limites

- Une syntaxe inconnue ou un appel à une fonction non autorisée provoque une erreur de compilation.
- Les types des variables et des arguments sont vérifiés avant l'exécution lorsque c'est possible.
- Les entrées user sont validées quand la réponse est reçue.
- Le script est limité à 1 000 actions.
- La compilation est limitée à 5 minutes et l'exécution à 5 minutes supplémentaires, soit 10 minutes maximum au total.
- Les boucles dépendant de l'état réel du serveur peuvent produire un nombre d'actions variable ; un compteur d'actions doit donc aussi être appliqué pendant l'exécution.
- Les opérations Discord restent soumises aux permissions du bot, à la hiérarchie des rôles et aux limites de l'API Discord.

## Exemple complet

```text
var username.input{str, "What is your username?"} = "";
var warnings.int = 0;
var enabled.bool = True;

if (enabled == True) {
    @send(f"Welcome {username}!");
}

for role in guild.role {
    if (role.name == "Old role") {
        @delete_role(role.id, "Obsolete role");
    }
}

repeat(3) {
    set warnings = warnings + 1;
}

@send(f"Number of checks: {warnings}");
```

---

**Note :** ce document formalise les règles prévues pour le langage. Les fonctions et propriétés doivent être vérifiées dans l'implémentation du bot avant d'être considérées comme disponibles dans une version publiée.
