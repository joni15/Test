"""
Monitoring Twitter/X avec deux modes :
  - Streaming (temps réel via Filtered Stream API) — nécessite Basic tier ($100/mois)
  - Polling toutes les N secondes (API gratuite, ~1 req/15min par endpoint)
"""
import asyncio
import logging
import time
from typing import Callable, Optional

import tweepy
import tweepy.asynchronous

from config import (
    X_BEARER_TOKEN, X_API_KEY, X_API_SECRET,
    X_ACCESS_TOKEN, X_ACCESS_SECRET,
    TARGET_USERNAME, POLL_INTERVAL_SEC, USE_STREAMING,
)

log = logging.getLogger(__name__)

TweetCallback = Callable[[str, str], None]  # (tweet_id, text) -> None


# ─────────────────────────────────────────────────────────────────────────────
# Mode 1 : Streaming temps réel
# ─────────────────────────────────────────────────────────────────────────────

class SnipingStreamListener(tweepy.StreamingClient):
    """Écoute en continu les nouveaux tweets du compte cible."""

    def __init__(self, bearer_token: str, callback: TweetCallback):
        super().__init__(bearer_token, wait_on_rate_limit=True)
        self._callback = callback

    def on_tweet(self, tweet: tweepy.Tweet):
        log.info(f"[STREAM] Tweet reçu id={tweet.id}")
        self._callback(str(tweet.id), tweet.text)

    def on_error(self, status):
        log.error(f"[STREAM] Erreur : {status}")

    def on_disconnect(self):
        log.warning("[STREAM] Déconnexion, reconnexion en cours…")


def start_stream(callback: TweetCallback) -> None:
    client = tweepy.Client(bearer_token=X_BEARER_TOKEN)

    # Récupérer l'user_id du compte cible
    user = client.get_user(username=TARGET_USERNAME)
    if not user.data:
        raise ValueError(f"Utilisateur @{TARGET_USERNAME} introuvable")
    user_id = user.data.id
    log.info(f"[STREAM] Surveillance de @{TARGET_USERNAME} (id={user_id})")

    stream = SnipingStreamListener(X_BEARER_TOKEN, callback)

    # Supprimer les règles existantes et en ajouter une nouvelle
    existing = stream.get_rules()
    if existing.data:
        stream.delete_rules([r.id for r in existing.data])

    stream.add_rules(tweepy.StreamRule(f"from:{user_id}"))
    log.info("[STREAM] Règle ajoutée, écoute active…")
    stream.filter(tweet_fields=["text", "created_at"])


# ─────────────────────────────────────────────────────────────────────────────
# Mode 2 : Polling (fallback gratuit)
# ─────────────────────────────────────────────────────────────────────────────

class PollingMonitor:
    """Interroge l'API toutes les POLL_INTERVAL_SEC secondes."""

    def __init__(self, callback: TweetCallback):
        self._client   = tweepy.Client(bearer_token=X_BEARER_TOKEN)
        self._callback = callback
        self._last_id: Optional[str] = None
        self._user_id: Optional[str] = None

    def _resolve_user(self) -> str:
        if self._user_id:
            return self._user_id
        resp = self._client.get_user(username=TARGET_USERNAME)
        if not resp.data:
            raise ValueError(f"Utilisateur @{TARGET_USERNAME} introuvable")
        self._user_id = str(resp.data.id)
        log.info(f"[POLL] @{TARGET_USERNAME} → id={self._user_id}")
        return self._user_id

    def _fetch_new_tweets(self) -> list[tuple[str, str]]:
        uid = self._resolve_user()
        kwargs = dict(
            id=uid,
            max_results=5,
            tweet_fields=["created_at", "text"],
            exclude=["retweets", "replies"],
        )
        if self._last_id:
            kwargs["since_id"] = self._last_id

        try:
            resp = self._client.get_users_tweets(**kwargs)
        except tweepy.TweepyException as e:
            log.warning(f"[POLL] Erreur API : {e}")
            return []

        if not resp.data:
            return []

        tweets = [(str(t.id), t.text) for t in resp.data]
        self._last_id = tweets[0][0]  # le plus récent est en premier
        return tweets

    def run(self) -> None:
        log.info(f"[POLL] Démarrage polling toutes les {POLL_INTERVAL_SEC}s")

        # Premier fetch : initialiser last_id sans déclencher de snipe
        try:
            initial = self._fetch_new_tweets()
            if initial:
                log.info(f"[POLL] Dernier tweet connu : {initial[0][0]}")
        except Exception as e:
            log.warning(f"[POLL] Init échouée : {e}")

        while True:
            time.sleep(POLL_INTERVAL_SEC)
            try:
                new_tweets = self._fetch_new_tweets()
                for tweet_id, text in reversed(new_tweets):  # chronologique
                    log.info(f"[POLL] Nouveau tweet {tweet_id}")
                    self._callback(tweet_id, text)
            except Exception as e:
                log.error(f"[POLL] Erreur inattendue : {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────────────────────────────────────

def start_monitor(callback: TweetCallback) -> None:
    if USE_STREAMING:
        log.info("[MONITOR] Mode : Streaming temps réel")
        try:
            start_stream(callback)
        except Exception as e:
            log.error(f"[MONITOR] Streaming échoué ({e}), bascule sur polling")
            PollingMonitor(callback).run()
    else:
        log.info("[MONITOR] Mode : Polling")
        PollingMonitor(callback).run()
