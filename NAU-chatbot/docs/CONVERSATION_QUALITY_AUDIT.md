# Validation conversationnelle IIT — 10 septembre 2026

## Périmètre

Analyse des quatre sessions présentes au début de l'audit : 79 messages, dont 40 demandes utilisateur. Les historiques d'origine sont conservés. Les reproductions utilisent de nouveaux comptes et de nouvelles sessions de test. Les transcriptions et résultats détaillés restent dans `.runtime/audit/`, hors Git ; ce document ne contient pas de données personnelles.

## Corrections

- Questions directes dès le premier message : programme, tarifs, certifications et autres informations disponibles sont donnés sans imposer d'abord une qualification commerciale.
- Questions multiples : composition des réponses sur les matières, certifications, débouchés, pratique, projets, stages, horaires, admission et tarifs. Une question sur le profil ne masque plus les informations déjà disponibles.
- Contexte : les réponses courtes au sujet du bac reprennent l'orientation ; une confirmation continue seulement l'action effectivement proposée. Les questions sur une formation déjà évoquée conservent cette formation.
- Parcours : une demande explicite de toutes les possibilités examine les formations actives avec les règles d'admissibilité. Les possibilités confirmées sont distinguées des cas à vérifier. Un nouveau bachelier n'est pas présenté comme directement admissible en cycle ingénieur.
- Contenu commercial : détails issus du catalogue, débouchés spécifiques à la spécialisation, distinction entre certification préparée et délivrée, absence de promesse d'emploi. Les modalités de pratique ou d'alternance absentes de la base sont signalées comme non documentées.
- Préinscription : utilisation du lien enregistré dans la base ; maintien de la distinction entre demande de préinscription et dossier après une préinscription déjà effectuée.

## Variantes et fautes

Deux mécanismes complémentaires évitent d'ajouter une expression régulière pour chaque nouvelle orthographe :

1. Comparaison dynamique des messages sociaux courts après réduction des répétitions de lettres. `cvn`, `cvnn`, `cvnnnnnn` et les salutations allongées utilisent le même calcul de similarité.
2. Interprétation sémantique par le modèle local pour les messages restés ambigus. Elle retourne un domaine, une reformulation et des intentions validées par un contrat. Elle peut router une expression sans correspondance dans les patterns. Cache limité à 128 interprétations pendant dix minutes, avec le contexte inclus dans la clé.

Les intentions déjà reconnues restent prioritaires. Les refus de sécurité, la résolution des faits du profil et les règles d'admission gardent leurs contrôles. Une sortie invalide ou peu sûre du modèle utilise le traitement de secours. Il ne s'agit pas d'un réentraînement des poids du modèle ni d'une garantie de compréhension de toute variante.

## Voix et disponibilité

Le service Whisper est chargé localement sur GPU. Les versions des dépendances scientifiques ont été rendues compatibles et FFmpeg est disponible pour décoder les enregistrements. Le hook du micro gère correctement le remontage React StrictMode et fournit un message exploitable en cas d'indisponibilité. Le format MP4 est accepté comme option d'enregistrement pour les navigateurs compatibles.

Test Chromium sur le tunnel HTTPS : connexion, clic micro avec une source audio française de test, arrêt, transcription HTTP 200, texte injecté dans le champ, puis envoi au chatbot HTTP 200. Aucune erreur JavaScript. Le test API vérifie également un enregistrement WebM.

Les services fonctionnent hors Docker. Le catalogue SQL du dépôt est chargé et l'index RAG a été reconstruit. Les commandes de démarrage et de contrôle sont décrites dans [LOCAL_TESTING.md](LOCAL_TESTING.md).

## Validation automatisée

- Backend : **310 tests réussis**, couvrant notamment les protections, l'admission, les profils, le contexte, les tarifs et les nouveaux cas conversationnels et sémantiques.
- Frontend : **55 tests réussis**, dont les régressions du micro ; compilation de production réussie.
- Rejeu public : **57 demandes dans huit nouvelles sessions**, toutes avec HTTP 200 ; médiane de 0,29 seconde, attentes de limitation de débit incluses. Les variantes ont ensuite fait l’objet d’un contrôle ciblé après les derniers ajustements. Résultats dans `.runtime/audit/full-replay-results.json` et `.runtime/audit/semantic-live-results.json`. Les réponses sont examinées sur leur contenu, pas seulement sur leur code HTTP.

Les questions structurées restent traitées sans génération libre. Une interprétation sémantique nouvelle peut prendre plusieurs secondes sur la T4 ; les cas reconnus par similarité et les interprétations en cache évitent cet appel. Les durées du rejeu public incluent le tunnel et, lorsque nécessaire, l'attente imposée par la limitation de débit. Ce contrôle ne constitue pas un test de charge ni une note universelle « 10/10 ».

Dernier contrôle après les ajustements sémantiques : sept demandes avec assertions de contenu dans deux nouvelles sessions, toutes réussies (`.runtime/audit/final-validation.json`). `cvnnnnnn` : 0,26–0,31 s ; `certifff` : 5,98 s au premier calcul, puis 0,62 s avec le cache. La demande sur les apprentissages concrets couvre la pratique sans ajouter de réponse sur le marché de l’emploi.

## Contrôle des dix derniers messages

Lecture des dix messages les plus récents au début de ce contrôle, avec le contexte antérieur des deux conversations concernées. La demande enregistrée « mouch bac letter chnouma les parcours fel iit nhb naraf kol chy » avait reçu tous les tarifs. La portée ALL (« kol chy ») reprenait FEES depuis l'ancien sujet lorsqu'aucune intention directe n'était détectée. Cette reprise empêchait l'interprétation sémantique de la nouvelle question.

La reprise du sujet précédent est maintenant réservée aux expressions de portée employées seules. Les nouvelles phrases passent par l'interprétation de leur propre demande. « nheb naraf kol chy al 9raya » et la demande enregistrée ont été vérifiées avec le modèle local : elles donnent le catalogue des études, sans tableau des tarifs. « kol chy » seul après une question de tarifs conserve son sens contextuel.

Le contrôle a aussi vérifié le dossier de préinscription, le programme d'architecture et les stages. Les informations correspondent au catalogue chargé. Les propositions de préinscription disposent désormais d'un délai entre deux relances. Une section de bac explicitement niée ne peut plus être réinscrite comme fait positif par le résolveur de profil.

Validation de cette correction : **319 tests backend réussis**, dont neuf nouveaux cas de changement de sujet, de négation et de répétition commerciale. Les historiques d'origine n'ont pas été modifiés. Les tests publics utilisent une nouvelle session ; les résultats restent dans `.runtime/audit/latest-public-results.json`.

## Darija et modération — contrôle complémentaire

Les nouveaux échanges réels ont confirmé deux injures non reconnues, à cause de préfixes et de variantes orthographiques : le chatbot retournait alors le catalogue. Le filtrage utilise maintenant une comparaison de mots normalisés (répétitions, translittération numérique et préfixes usuels), avant les intentions académiques. Les variantes testées des expressions signalées sont bloquées, y compris dans une question mixte contenant « tarifs ». Les mots proches mais non injurieux comme « 7asba », « Kasba » et « kahraba » ne sont pas bloqués par ce filtre.

Un classement social court par le modèle complète la reconnaissance : accord, remerciement, salutation ou clarification. Le prompt donne des repères linguistiques tunisiens, sans ajouter une regex pour chaque variante. `mrigel`, `mrigelll` et `mriigelll` sont reconnus comme un accord par le modèle réel. Le premier contrôle classait `yehik` comme une clarification ; le contrôle des remerciements ci-dessous corrige cette interprétation après précision de son usage par l’utilisateur. Les résultats sont mis en cache. Le modèle seul ayant échoué sur certaines injures lors des essais, la modération ne dépend pas uniquement de sa classification. Une classification sémantique INAPPROPRIATE refuse également le message et restaure la mémoire du profil.

La réponse sur la pratique en architecture cite désormais les compétences de projets architecturaux présentes au catalogue, en les qualifiant comme compétences au programme. Elle ne déduit pas un volume horaire de pratique non renseigné.

**341 tests backend réussis** après ce complément. Les observations détaillées restent hors Git dans `.runtime/audit/darija-probe.log`, `.runtime/audit/social-final-probe.log` et `.runtime/audit/darija-public.log`. Cette validation couvre les cas observés et les variantes testées ; elle ne prouve pas une reconnaissance universelle de toutes les expressions et insultes inédites.

## Présentation des réponses et continuité de lecture

Les réponses de détail commencent désormais par l'information demandée. Le bloc systématique titre / lien / diplôme a été supprimé. Le diplôme et la durée figurent dans une présentation générale quand ils sont utiles ; une question sur la durée reçoit une réponse courte. Les programmes longs utilisent des listes, les certifications un paragraphe et les stages une réponse ciblée.

Le lien de formation apparaît à la fin lors de la première présentation ou d'un changement de formation ; il reste accessible sur demande. Les réponses suivantes sur la même formation ne le répètent pas. La liste des spécialisations n'est pas répétée lorsque l'utilisateur poursuit les questions sur le programme, sauf demande explicite. Le catalogue général conserve toutes les formations avec un seul lien de référence.

Les réponses factuelles sur le programme, les certifications, les projets et les stages ne se terminent plus systématiquement par une invitation à se préinscrire. Les conditions et réserves utiles sont conservées. Une même preuve documentaire n'est pas répétée dans les rubriques pratique et projets ; leur réserve commune est donnée une seule fois. Cette présentation utilise les faits structurés existants, sans ajouter d'appel de génération.

Validation : **346 tests backend réussis**. Neuf demandes publiques réparties sur trois nouvelles sessions ont vérifié les réponses successives, le changement de formation, les questions multiples et le catalogue. Résultats privés : `.runtime/audit/response-ux-results.json`.

Le parcours programme → stages → pratique → durée a aussi été testé dans Chromium sur le tunnel HTTPS : listes rendues correctement, lien absent des réponses de suivi, aucune erreur JavaScript. Les précisions finales s'adaptent au sujet (conditions du stage, volume de pratique, encadrement des projets) pour éviter la même phrase de réserve à chaque réponse. Capture locale : `.runtime/audit/response-ux-browser.png`.

## Remerciements tunisiens et injures masquées

Le contrôle avec le modèle réel reconnaissait déjà `aychek` et `ybereklek`, mais classait `yehik` en clarification et `yeftah alik` en accord. Les consignes des deux interpréteurs précisent maintenant leur usage comme remerciements, ainsi que les souhaits bienveillants adressés à celui qui aide. La généralisation porte sur la translittération, les variantes phonétiques et les lettres répétées, sans nouvelle regex par variante. Une question universitaire accompagnée d'un merci garde ses intentions académiques.

Les quatre expressions ont reçu une réponse de remerciement sur l'API publique, seules puis après une discussion de formation. Les variantes `3aychekkk`, `yehikkk`, `yefta7 3lik`, `ybarklekk`, la formule `rabi ybareklek w yeftah alik` et `ya3tik sa7a` ont aussi été vérifiées. Le premier rejeu contenait une assertion de programme trop spécifique (`Programmation`, absent des huit premiers éléments réellement affichés) ; le contrôle final vérifie les matières effectivement présentes et le stage, et conserve le résultat initial pour traçabilité.

Le filtre local bloquait déjà `ezzebi` et `fok ala ezzebi`, mais laissait passer `barra neyk`, `barra neyek` et les lettres séparées. La modération dispose désormais d'une vue normalisée qui retire les caractères invisibles et les séparateurs insérés dans un mot. Les suites de lettres isolées sont également comparées au lexique. Une comparaison consonantique est réservée aux lexèmes explicitement autorisés dans `phonetic_vocabulary`, avec au moins trois consonnes distinctives : cela couvre les variantes vocaliques de `nayek`, sans étendre cette tolérance à tous les mots courts. Le texte original reste utilisé pour le dialogue.

Ces refus précèdent les intentions académiques et n'exigent aucun appel au modèle. Les tests simulent un modèle indisponible et vérifient la conservation intégrale du profil et des actions en attente. Des mots inoffensifs, remerciements, noms et expressions comme `7asba`, `Kasba`, `Nabeul`, `New York`, `nylon`, `noyau` et `e-learning` ne déclenchent pas le filtre. Cette couverture ciblée ne garantit pas la détection de toute injure ou de tout masquage inédit.

Validation automatisée : **376 tests backend réussis**. **18 demandes publiques réussies**, avec assertions sur le contenu : neuf refus, six remerciements, deux questions de programme et une reprise de durée après les refus. Les résultats du contrôle public final sont conservés dans `.runtime/audit/moderation-public-results.json`. Les services sont actifs hors Docker.

## Audit de la conversation commençant par « aaa »

Lecture de 119 messages enregistrés dans les trois conversations utilisateur récentes : 60 messages utilisateur et 59 réponses. La session « aaa » comprend onze échanges. Elle présentait quatre répétitions du même refus d'orientation, une question d'identité classée hors sujet, une précision de spécialité ignorée et un choix de formation renvoyé vers le catalogue général. Les services étaient disponibles ; ces échecs relevaient principalement de la compréhension et du suivi du dialogue.

Corrections :

- Un message réduit à la répétition d'une seule lettre obtient une clarification immédiate. Une question d'identité reçoit une présentation du rôle de l'assistant. Les demandes d'explication reprennent la précision attendue dans la conversation.
- Une spécialité abrégée telle que `indus` est confrontée aux intitulés de diplômes d'origine présents dans les règles. Si plusieurs intitulés plus précis correspondent, l'assistant demande le diplôme exact au lieu de conclure qu'aucune orientation n'existe. Il distingue le projet d'études, la validation de la licence et la précision du titre dans ses réponses successives.
- Une précision libre du diplôme peut être interprétée par le modèle. Le test réel a révélé que celui-ci ajoutait parfois « maintenance » à « industrielle ». Les mots sans appui dans le message sont désormais écartés avant toute écriture de spécialité. La normalisation du préfixe « licence en » dans la comparaison des diplômes ne crée aucune nouvelle équivalence d'admission.
- Un niveau inférieur annoncé après une licence déclenche une question de clarification, sans effacer silencieusement le profil connu. Une correction ensuite confirmée remplace le niveau et efface les données de licence et la recommandation devenues obsolètes.
- Le choix explicite d'une formation est résolu avant l'interprétation générale. Un extrait copié du catalogue, comme « Cycle Ingénieur — Génie Industriel — 3 ans », affiche cette formation. Les fautes proches dans les noms de diplômes sont normalisées avec des garde-fous ; les mots ordinaires comme « matière » restent inchangés.
- Une question de spécialité en attente n'est plus considérée comme résolue uniquement parce qu'une ancienne valeur existe déjà. Les anciennes sessions peuvent aussi préciser leur spécialité sans recommencer la conversation.

Les historiques d'origine sont conservés. Le rejeu public utilise de nouvelles sessions et vérifie les réponses, pas seulement HTTP 200. Les attentes dues à la limite de débit sont respectées et figurent dans les durées mesurées. Certaines interprétations nouvelles par le modèle local prennent encore plusieurs secondes ; les questions reconnues et les choix de formation évitent cet appel.

Traces privées : `.runtime/audit/aaa-context.json`, `.runtime/audit/total-replay-results.json`. Les assertions de non-régression couvrent aussi l'absence d'ajout de diplôme par le modèle, la correction de profil, les titres d'origine exacts et la reprise d'une ancienne session.

Le contrôle complémentaire avec une licence en maintenance industrielle a révélé une autre cause : lorsqu'un intérêt spécifique était reconnu, le moteur ne construisait des candidats qu'à partir des sous-spécialisations. Les formations sans sous-spécialisation étaient donc éliminées. Elles restent désormais candidates au niveau de la formation, avec les mêmes contrôles d'admission. Un test traverse l'extraction de profil, le moteur réel de recommandation et les règles réelles de la fixture ; il ne remplace plus la recommandation par une réponse simulée pour ce cas.

Validation finale : **392 tests backend**, **55 tests frontend**, compilation de production réussie. **60 messages rejoués sur le tunnel public**, puis **5 contrôles complémentaires réussis** sur la clarification rapide, le diplôme exact, l'admission en Génie Industriel et la correction vers le bac. Médiane du rejeu : 0,275 seconde ; les interprétations nouvelles restent plus lentes et les attentes de limitation de débit sont comptées séparément dans l'analyse des cas.

Nouveau contrôle Chromium du micro : transcription HTTP 200, texte injecté dans le champ, envoi au chatbot HTTP 200, aucune erreur JavaScript. Un premier envoi avait rencontré HTTP 429 pendant le rejeu intensif ; la limite a été respectée et le parcours a ensuite été validé. Résultats complémentaires : `.runtime/audit/aaa-final-check.json` et `.runtime/audit/browser-voice.png`. Backend relancé avec les derniers correctifs ; frontend, PostgreSQL, Redis, Chroma, inférence et transcription disponibles hors Docker.
