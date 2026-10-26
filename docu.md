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
var username.str = "Alex"
var attempts.int = 3
var ratio.float = 1.5
var enabled.bool = True
var target.user.id = ""
var channels.list = ()
var configuration.dict = []
var wait.time = 10
set essais = 4
```

`""` signifie vide/non renseigné lors de l'initialisation, y compris pour les types autres que `str`. Une liste vide s'écrit `()`, un dictionnaire vide `[]`. `set nom = valeur` modifie une variable existante, sans répéter son type ; une valeur incompatible produit une erreur de type.

## Opérateurs et expressions

Arithmétique : `+`, `-`, `*`, `/`, `%`.

Compareason : `==`, `!=`, `<`, `>`, `<=`, `>=`. Les types comparés doivent être compatibles.

Logique : `&&` signifie ET, `!!` signifie OU et `#` signifie NON. Les parenthèses regroupent les expressions. Les priorités suivent les règles usuelles des expressions.

## Conditions

```text
if (essais >= 3 && actif == True) {
    @send("Conditions met");
} elif (essais > 0) {
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

for member in guild.user {
    @send(member.name);
}

for i in range(0, 5) {
    @send(f"Tour {i}");
}
```

`repeat(n)` répète le bloc n fois. `for variable in collection` parcourt une collection. `range(debut, fin)` inclut le début et exclut la fin : `range(0, 5)` produit 0 à 4. Les collections Discord doivent être parcourues sur un instantané stable si le script les modifie.

## Chaînes formatées

```text
var username.str = "Alex"
var score.int = 12
@send(f"Player: {pseudo}, score: {score}");
@send(f"Prochain score: {score + 1}");
```

Les expressions valides dans une chaîne `f"…"` sont évaluées. Si une portion entre accolades ne peut pas être analysée comme expression, elle est conservée telle quelle dans le texte.

## Listes et dictionnaires

Les listes utilisent des parenthèses, les positions commencent à zéro :

```text
var numbers.list = (10, 20, 30)
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

## Entrées user

Une entrée est déclarée avec `.input` suivi du type attendu et de la question. `input` est un modificateur de déclaration, pas un type.

```text
var username.input{str, "What is your username?"} = ""
var age.input{int, "How old are you?"} = ""
var actif.input{bool, "Enable this feature?"} = False
var cible.input{user.id, "What is the Discord ID?"} = ""
```

Types pris en charge par les entrées : `str`, `int`, `float`, `bool`, `user.id`, `channel.id`, `category.id`, `role.id` et `message.id`. Les entrées de type liste et dictionnaire ne sont pas prises en charge.

Fonctionnement prévu :

1. Le bot envoie la question dans le channel où le script a été lancé.
2. Il attend la prochaine réponse de la personne qui a lancé le script.
3. La réponse est convertie et validée selon le type attendu.
4. Le délai d'attente est d'une minute.
5. En cas de réponse invalide ou de délai dépassé, le script s'arrête. Il n'y a pas de seconde tentative dans la même exécution : il faut relancer le script.

Une entrée booléenne doit permettre d'obtenir `True` ou `False`.

## Objets et collections Discord

### Collections

- `guild.member` : members du serveur.
- `guild.channel` : channels du serveur.
- `guild.role` : rôles du serveur.

Sans propriété, une collection ou un objet ciblé par défaut représente son identifiant. Une propriété explicite permet d'accéder à une autre donnée.

### Propriétés

| Objet | Propriétés prévues |
|---|---|
| Utilisateur/member | `.id`, `.name`, `.display_name`, `.bot`, `.role` |
| Salon (`channel`) | `.id`, `.name`, `.category`, `.perm`, `.slowmode`, `.type` |
| Catégorie | `.id`, `.name`, `.perm` |
| Rôle | `.id`, `.name`, `.color`, `.perm`, `.position`, `.managed` |
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

Tous les appels de fonctions commencent par `@`. Seules les fonctions répertoriées et effectivement implémentées dans la version du bot sont utilisables.

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
| `@mute(user, durée, reason?)` | Utilisateur, durée, reason facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@unmute(user, reason?)` | Utilisateur, reason facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |

### Salons et categorys

| Fonction | Rôle |
|---|---|
| `@create_chanel(nom, perm?, categorie?)` | Crée un channel et doit renvoyer son identifiant `channel.id` en cas de succès. |
| `@delete_chanel(id, reason?)` | Supprime un channel. |
| `@set_chanel.name{chanel_id, nom}` | Modifie le nom d'un channel. |
| `@set_chanel.color{chanel_id, color}` | Modifie une color lorsque cette propriété s'applique à la cible. |
| `@set_chanel.perm{chanel_id, permission:True;autre_permission:False}` | Modifie une ou plusieurs permissions du channel. |
| `@slowmode(chanel, seconds)` | Configure le mode lent du channel. |
| `@lock(chanel)` | Verrouille le channel selon les permissions Discord. |
| `@unlock(chanel)` | Retire le verrouillage appliqué par le bot. |

### Rôles

| Fonction | Rôle |
|---|---|
| `@create_role(nom, color?, perm?)` | Crée un rôle et doit renvoyer son identifiant `role.id` en cas de succès. |
| `@delete_role(id, reason?)` | Supprime un rôle. |
| `@set_role.name{role_id, nom}` | Modifie le nom d'un rôle. |
| `@set_role.color{role_id, "#RRGGBB"}` | Modifie la color d'un rôle. |
| `@set_role.perm{role_id, permission:True;autre_permission:False}` | Modifie une ou plusieurs permissions du rôle. |
| `@give_role(user, role)` | Attribue un rôle à un user. |

Pour `.perm`, chaque permission reçoit `True` ou `False`. Plusieurs changements peuvent être séparés par des points-virgules. Les noms de permissions acceptés doivent correspondre aux permissions Discord prises en charge par le bot.

### Messages

| Fonction | Rôle |
|---|---|
| `@send(message)` | Envoie un message dans le channel où le script a été lancé. |
| `@send(chanel, message)` | Envoie un message dans le channel indiqué. |
| `@dm(user, message)` | Envoie un message privé à l'user. |
| `@clear(nombre)` | Supprime le nombre de messages indiqué, dans les limites imposées par Discord. |

Les messages peuvent être des chaînes normales ou formatées : `@send(f"Welcome {member.name} !")`.

## Durées

Le type `time` représente une durée. Sans suffixe, la valeur est exprimée en minutes.

| Suffixe | Unité |
|---|---|
| aucun | minutes |
| `s`, `sec` | seconds |
| `m`, `min` | minutes |
| `h` | heures |
| `d` | jours |

Les suffixes ne sont pas sensibles à la casse.

```text
var court.time = 30sec
var standard.time = 10
var long.time = 2h
@mute(cible, standard, "Spam");
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
var username.input{str, "What is your username?"} = ""
var warnings.int = 0
var enabled.bool = True

if (actif == True) {
    @send(f"Welcome {pseudo} !");
}

for role in guild.role {
    if (role.name == "Old role") {
        @delete_role(role.id, "Obsolete role");
    }
}

repeat(3) {
    set avertissements = avertissements + 1
}

@send(f"Number of checks : {avertissements}");
```

---

**Note :** ce document formalise les règles prévues pour le langage. Les fonctions et propriétés doivent être vérifiées dans l'implémentation du bot avant d'être considérées comme disponibles dans une version publiée.
