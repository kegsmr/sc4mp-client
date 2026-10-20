from __future__ import annotations

import time
from itertools import count
from threading import Lock, Condition


class EventChannel:


	MAX_EVENTS = 10000	# more than a server's chat history


	def __init__(self):

		self._lock = Lock()
		self._condition = Condition(self._lock)
		self._events: dict[int, list[dict]] = {}
		self._users: dict[int, str] = {}	# the user ID of each subscription
		self._contexts: dict[int, dict] = {}	# extra values for the user's `user_join` and `user_leave` events (eg. their name)
		self._subscription_ids = count()


	def subscribe(self, user_id: str, events=None, context=None) -> int:
		"""Returns a subscription ID to pass to `listen` and `unsubscribe`. A user can have several subscriptions (eg. a reconnect before the old connection is noticed to be closed). `events` are sent to the new subscription first (eg. recent chat messages). `context` is added to the user's `user_join` and `user_leave` events."""

		context = context or {}

		with self._lock:
			subscription_id = next(self._subscription_ids)
			joined = user_id not in self._users.values()
			self._events[subscription_id] = list(events or [])
			self._users[subscription_id] = user_id
			self._contexts[subscription_id] = context

		if joined:
			self.push('user_join', {**context, 'user_id': user_id}, exclude=[user_id])

		return subscription_id


	def unsubscribe(self, subscription_id: int):

		with self._lock:
			if not subscription_id in self._events:
				return
			self._events.pop(subscription_id)
			user_id = self._users.pop(subscription_id)
			context = self._contexts.pop(subscription_id)
			left = user_id not in self._users.values()

		if left:
			self.push('user_leave', {**context, 'user_id': user_id}, exclude=[user_id])


	def push(self, event_type: str, event_context: dict, exclude=None):

		event = {
			'event': event_type,
			**event_context
		}

		with self._condition:
			for subscription_id, events in self._events.items():
				if exclude and self._users[subscription_id] in exclude:
					continue
				events.append(event)
				while len(events) > self.MAX_EVENTS:
					events.pop(0)
			self._condition.notify_all()


	def listen(self, subscription_id: int, timeout=5) -> list[dict]:

		with self._condition:

			if subscription_id not in self._events:
				raise ValueError(
					f"Subscription {subscription_id!r} is not subscribed to the event channel."
				)

			while not self._events[subscription_id]:
				if not self._condition.wait(timeout):
					return []

			events = list(self._events[subscription_id])
			self._events[subscription_id].clear()

		return events
