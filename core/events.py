from __future__ import annotations

from threading import Lock


class EventsChannel:


	def __init__(self):

		self._lock = Lock()
		self._events: dict[str, list[dict]] = {}


	def subscribe(self, user_id: str):

		self.push('user_join', {'user_id': user_id})

		with self._lock:
			self._events.setdefault(user_id, [])


	def unsubscribe(self, user_id: str):

		if not user_id:
			return

		with self._lock:
			if not user_id in self._events:
				return
			self._events.pop(user_id)
		
		self.push('user_leave', {'user_id': user_id})

	
	def push(self, event_type: str, event_context: dict, exclude=None):

		event = {
			'event': event_type,
			**event_context
		}

		print(event)

		with self._lock:
			user_ids = list(self._events.keys())
			for user_id in user_ids:
				if exclude and user_id in exclude:
					continue
				self._events[user_id].append(event)


	def get(self, user_id) -> list[dict]:

		with self._lock:
			if user_id not in self._events:
				raise ValueError(
					f"User {user_id!r} is not subscribed to the event channel."
				)
			events = list(self._events[user_id])
			self._events[user_id].clear()

		return events
