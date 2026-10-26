# `.exe` — langage de scripts pour Discord

`.exe` est un bot Discord Python qui propose un langage de script dédié aux actions Discord. Ce langage **n'est pas Python** : seules les instructions autorisées par le moteur sont acceptées.

## Source de vérité

La documentation du langage est dans **[`docu.md`](docu.md)**. Les exemples de ce README suivent sa syntaxe moderne : déclarations typées avec `var`, appels natifs préfixés par `@`, blocs entre accolades et point-virgule obligatoire après chaque instruction.

## Exemple

```text
var greeting.str = "Hello";
var count.int = 3;

if (count == 3) {
    @send(f"{greeting}: {count}");
} else {
    @send("Not enough");
}

repeat(2) {
    @send("Done");
}
```

Les retours à la ligne sont facultatifs **après** un `;`. Les instructions peuvent donc être enchaînées sur une seule ligne. Les accolades ouvrantes des blocs et les accolades fermantes ne prennent pas de point-virgule. Les syntaxes historiques (`let`, `send(...)` sans `@`, `m(...)`, `v(...)`, `R(...)`, `I(...)`, `E(...)`) ne font pas partie du langage moderne.

## Utilisation du bot

- `!exe <script>` — compile puis exécute un script.
- `!exe create <name> :: <script>` — valide et enregistre un script.
- `!exe list` — liste tes scripts enregistrés.
- `!exe run <name>` — exécute l'un de tes scripts.
- `!exe delete <name>` — supprime l'un de tes scripts.
- `!exe admin add @user`, `!exe admin remove @user`, `!exe admin list` — commandes réservées au propriétaire configuré.

Seuls les utilisateurs autorisés par la whitelist peuvent lancer ou gérer leurs scripts. Les actions Discord restent soumises aux permissions effectives et à la hiérarchie des rôles.

## Installation

Python 3.12 ou plus récent est requis.

```sh
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
python -m pip install -e .
```

Copie `.env.example` vers `.env`, renseigne `DISCORD_TOKEN` et `OWNER_ID`, puis démarre le bot avec la commande de lancement du projet.

## Tests

```sh
python -m pip install -e . pytest
python -m pytest
```

## Sécurité et limites

Le moteur utilise une liste d'instructions autorisées et n'est pas conçu pour exécuter du Python arbitraire. Les scripts ont des limites de taille, d'actions et de temps. Ne partage jamais ton token Discord. Consulte `docu.md` pour la syntaxe documentée et vérifie les fonctionnalités prises en charge par la version installée.
