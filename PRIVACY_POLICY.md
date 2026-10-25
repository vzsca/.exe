# Politique de confidentialité de .exe

Dernière mise à jour : 25 octobre 2026

## 1. Périmètre et responsable
.exe est un logiciel open source qui s’exécute sur l’infrastructure de la personne qui l’installe. Le responsable du traitement dépend donc de l’exploitant de chaque instance. Cette page décrit le comportement prévu par le dépôt ; l’exploitant doit la vérifier avant de publier ou d’héberger le bot.

## 2. Données traitées par le logiciel
Selon les commandes utilisées, le bot peut traiter :
- les identifiants Discord de l’auteur d’une commande et des cibles d’actions de modération ;
- les identifiants de serveur, salon et rôles nécessaires à l’exécution des commandes ;
- le contenu des commandes et scripts, ainsi que les réponses fournies à la fonction `input()` ;
- les scripts nommés sauvegardés, associés à l’identifiant Discord de leur créateur ;
- les identifiants inscrits dans la liste blanche ;
- des informations techniques et erreurs écrites dans les journaux par l’application.

Les scripts enregistrés et la liste blanche sont stockés dans la base SQLite configurée par l’exploitant. Les journaux peuvent contenir des métadonnées d’exécution et des identifiants. L’exploitant doit vérifier le code et la configuration de sa version pour confirmer exactement les données conservées.

## 3. Finalités et base de traitement
Ces données servent à exécuter les commandes, appliquer les autorisations, sauvegarder les scripts demandés, gérer la liste blanche, diagnostiquer les erreurs et protéger le bot contre les usages non autorisés. Pour une instance utilisée dans un cadre soumis au RGPD, l’exploitant doit déterminer et documenter la base légale applicable.

## 4. Destinataires et services tiers
Les commandes sont traitées par le bot hébergé par l’exploitant et transmises à Discord via son API. Discord traite ces données conformément à ses propres conditions et à sa politique de confidentialité. L’accès à la base SQLite et aux journaux doit être limité à l’exploitant et aux personnes autorisées.

## 5. Conservation et sécurité
La durée de conservation dépend de la configuration et des pratiques de l’exploitant. Les scripts et entrées de liste blanche peuvent être supprimés via les fonctionnalités disponibles ou directement dans la base de données. Protégez le fichier SQLite, les journaux, les sauvegardes et le fichier `.env`; ne publiez jamais le jeton du bot. Ne stockez pas de données sensibles dans les scripts ou leurs entrées.

## 6. Droits et contact
Les demandes d’accès, de rectification ou de suppression doivent être adressées à l’exploitant de l’instance, qui doit répondre selon la législation applicable. Pour le dépôt logiciel, signalez les questions ou corrections via https://github.com/vzsca/.exe/issues.

## 7. Limites de ce document
Cette politique est un modèle de départ et ne garantit pas à elle seule la conformité au RGPD. Avant toute mise en service, l’exploitant doit confirmer les traitements réels, ajouter ses coordonnées, préciser les durées de conservation, les éventuels transferts et les modalités d’exercice des droits.
