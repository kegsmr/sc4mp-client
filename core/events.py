from __future__ import annotations

import time
from threading import Lock, Condition


class EventChannel:


	MAX_EVENTS = 1000


	def __init__(self):

		self._lock = Lock()
		self._condition = Condition(self._lock)
		self._events: dict[str, list[dict]] = {}


	def subscribe(self, user_id: str):

		with self._lock:
			if user_id in self._events:
				return
			self._events.setdefault(user_id, [])

		self.push('user_join', {'user_id': user_id}, exclude=[user_id])


	def unsubscribe(self, user_id: str):

		if not user_id:
			return

		with self._lock:
			if not user_id in self._events:
				return
			self._events.pop(user_id)
		
		self.push('user_leave', {'user_id': user_id}, exclude=[user_id])

	
	def push(self, event_type: str, event_context: dict, exclude=None):

		event = {
			'event': event_type,
			**event_context
		}

		print(event)

		with self._condition:
			user_ids = list(self._events.keys())
			for user_id in user_ids:
				if exclude and user_id in exclude:
					continue
				self._events[user_id].append(event)
				while len(self._events[user_id]) > self.MAX_EVENTS:
					self._events[user_id].pop(0)
			self._condition.notify_all()


	def listen(self, user_id, timeout=5) -> list[dict]:

		with self._condition:

			if user_id not in self._events:
				raise ValueError(
					f"User {user_id!r} is not subscribed to the event channel."
				)
			
			while not self._events[user_id]:
				if not self._condition.wait(timeout):
					return []

			events = list(self._events[user_id])
			self._events[user_id].clear()

		return events
