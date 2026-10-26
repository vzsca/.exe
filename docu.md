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

Les expressions valides dans une chaîne `f"…"` sont évaluées. Si une portion entre accolades ne peut pas être analysée comme expression, elle est conservée telle quelle dans le texte.

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

## Entrées utilisateur

Une entrée est déclarée avec `.input` suivi du type attendu et de la question. `input` est un modificateur de déclaration, pas un type.

```text
var pseudo.input{str, "Quel est ton pseudo ?"} = ""
var age.input{int, "Quel âge as-tu ?"} = ""
var actif.input{bool, "Activer la fonctionnalité ?"} = False
var cible.input{user.id, "Quel est l'identifiant Discord ?"} = ""
```

Types pris en charge par les entrées : `str`, `int`, `float`, `bool`, `user.id`, `chanel.id`, `categorie.id`, `role.id` et `message.id`. Les entrées de type liste et dictionnaire ne sont pas prises en charge.

Fonctionnement prévu :

1. Le bot envoie la question dans le salon où le script a été lancé.
2. Il attend la prochaine réponse de la personne qui a lancé le script.
3. La réponse est convertie et validée selon le type attendu.
4. Le délai d'attente est d'une minute.
5. En cas de réponse invalide ou de délai dépassé, le script s'arrête. Il n'y a pas de seconde tentative dans la même exécution : il faut relancer le script.

Une entrée booléenne doit permettre d'obtenir `True` ou `False`.

## Objets et collections Discord

### Collections

- `guild.user` : membres du serveur.
- `guild.chanel` : salons du serveur.
- `guild.role` : rôles du serveur.

Sans propriété, une collection ou un objet ciblé par défaut représente son identifiant. Une propriété explicite permet d'accéder à une autre donnée.

### Propriétés

| Objet | Propriétés prévues |
|---|---|
| Utilisateur/membre | `.id`, `.name`, `.display_name`, `.bot`, `.role` |
| Salon (`chanel`) | `.id`, `.name`, `.category`, `.perm`, `.slowmode`, `.type` |
| Catégorie | `.id`, `.name`, `.perm` |
| Rôle | `.id`, `.name`, `.color`, `.perm`, `.position`, `.managed` |
| Message | `.id`, `.content`, `.author`, `.channel` |

La disponibilité exacte d'une propriété doit être vérifiée dans l'implémentation du bot et dépend de l'objet Discord. Le langage ne donne pas accès à des attributs Python arbitraires.

```text
for role in guild.role {
    if (role.name == "Ancien rôle") {
        @delete_role(role.id, "Nettoyage");
    }
}

if ("Modérateur" in guild.role.name) {
    @send("Le rôle Modérateur existe");
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
| `@ban(user, raison?)` | Utilisateur, raison facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@kick(user, raison?)` | Utilisateur, raison facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@unban(user_id)` | Identifiant utilisateur uniquement | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@mute(user, durée, raison?)` | Utilisateur, durée, raison facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |
| `@unmute(user, raison?)` | Utilisateur, raison facultative | `True` en cas de succès ; sinon `False` avec une erreur explicative |

### Salons et catégories

| Fonction | Rôle |
|---|---|
| `@create_chanel(nom, perm?, categorie?)` | Crée un salon et doit renvoyer son identifiant `chanel.id` en cas de succès. |
| `@delete_chanel(id, raison?)` | Supprime un salon. |
| `@set_chanel.name{chanel_id, nom}` | Modifie le nom d'un salon. |
| `@set_chanel.color{chanel_id, couleur}` | Modifie une couleur lorsque cette propriété s'applique à la cible. |
| `@set_chanel.perm{chanel_id, permission:True;autre_permission:False}` | Modifie une ou plusieurs permissions du salon. |
| `@slowmode(chanel, secondes)` | Configure le mode lent du salon. |
| `@lock(chanel)` | Verrouille le salon selon les permissions Discord. |
| `@unlock(chanel)` | Retire le verrouillage appliqué par le bot. |

### Rôles

| Fonction | Rôle |
|---|---|
| `@create_role(nom, couleur?, perm?)` | Crée un rôle et doit renvoyer son identifiant `role.id` en cas de succès. |
| `@delete_role(id, raison?)` | Supprime un rôle. |
| `@set_role.name{role_id, nom}` | Modifie le nom d'un rôle. |
| `@set_role.color{role_id, "#RRGGBB"}` | Modifie la couleur d'un rôle. |
| `@set_role.perm{role_id, permission:True;autre_permission:False}` | Modifie une ou plusieurs permissions du rôle. |
| `@give_role(user, role)` | Attribue un rôle à un utilisateur. |

Pour `.perm`, chaque permission reçoit `True` ou `False`. Plusieurs changements peuvent être séparés par des points-virgules. Les noms de permissions acceptés doivent correspondre aux permissions Discord prises en charge par le bot.

### Messages

| Fonction | Rôle |
|---|---|
| `@send(message)` | Envoie un message dans le salon où le script a été lancé. |
| `@send(chanel, message)` | Envoie un message dans le salon indiqué. |
| `@dm(user, message)` | Envoie un message privé à l'utilisateur. |
| `@clear(nombre)` | Supprime le nombre de messages indiqué, dans les limites imposées par Discord. |

Les messages peuvent être des chaînes normales ou formatées : `@send(f"Bienvenue {membre.name} !")`.

## Durées

Le type `time` représente une durée. Sans suffixe, la valeur est exprimée en minutes.

| Suffixe | Unité |
|---|---|
| aucun | minutes |
| `s`, `sec` | secondes |
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
- Les entrées utilisateur sont validées quand la réponse est reçue.
- Le script est limité à 1 000 actions.
- La compilation est limitée à 5 minutes et l'exécution à 5 minutes supplémentaires, soit 10 minutes maximum au total.
- Les boucles dépendant de l'état réel du serveur peuvent produire un nombre d'actions variable ; un compteur d'actions doit donc aussi être appliqué pendant l'exécution.
- Les opérations Discord restent soumises aux permissions du bot, à la hiérarchie des rôles et aux limites de l'API Discord.

## Exemple complet

```text
var pseudo.input{str, "Quel est ton pseudo ?"} = ""
var avertissements.int = 0
var actif.bool = True

if (actif == True) {
    @send(f"Bienvenue {pseudo} !");
}

for role in guild.role {
    if (role.name == "Ancien rôle") {
        @delete_role(role.id, "Rôle obsolète");
    }
}

repeat(3) {
    set avertissements = avertissements + 1
}

@send(f"Nombre de vérifications : {avertissements}");
```

---

**Note :** ce document formalise les règles prévues pour le langage. Les fonctions et propriétés doivent être vérifiées dans l'implémentation du bot avant d'être considérées comme disponibles dans une version publiée.
