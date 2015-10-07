# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from actors.internal.mailbox import InternalMailbox
from .mock_compat import Mock


@pytest.fixture
def actor():
    actor = Mock()
    actor.handle_message = Mock()
    actor.handle_system_message = Mock()
    return actor


@pytest.fixture
def mailbox(actor):
    return InternalMailbox(Mock(), actor)


def test_should_invoke_handle_message_on_actor(actor, mailbox):
    message = object()
    mailbox.enqueue(message)
    mailbox.process_messages()
    actor.handle_message.assert_called_once_with(message)


def test_should_invoke_handle_system_message_on_actor(actor, mailbox):
    message = object()
    mailbox.enqueue_system(message)
    mailbox.process_messages()
    actor.handle_system_message.assert_called_once_with(message)


def test_should_process_system_messages_before_user_messages(actor, mailbox):
    mailbox.enqueue(1)
    mailbox.enqueue_system(2)

    def assert_handle_message_not_called(*args, **kwargs):
        assert not actor.handle_message.called
    actor.handle_system_message.side_effect = assert_handle_message_not_called

    mailbox.process_messages()
    actor.handle_system_message.assert_called_once_with(2)
    actor.handle_message.assert_called_once_with(1)


def test_should_stop_processing_when_reaching_throughput_limit(actor):
    mailbox = InternalMailbox(Mock(), actor, throughput=2)
    mailbox.enqueue(1)
    mailbox.enqueue(1)
    mailbox.enqueue(1)
    mailbox.process_messages()
    assert actor.handle_message.call_count == 2


def test_should_not_processing_user_messages_when_suspended(actor, mailbox):
    mailbox.suspend()
    mailbox.enqueue(Mock())
    mailbox.process_messages()
    assert not actor.handle_system_message.called


def test_should_process_system_messages_when_suspended(actor, mailbox):
    mailbox.suspend()
    mailbox.enqueue_system(Mock())
    mailbox.process_messages()
    assert actor.handle_system_message.called


def test_should_not_process_system_messages_when_closed(actor, mailbox):
    mailbox.close()
    mailbox.enqueue_system(Mock())
    mailbox.process_messages()
    assert not actor.handle_system_message.called


def test_should_process_user_messages_on_resume(actor, mailbox):
    mailbox.suspend()
    mailbox.enqueue(Mock())
    mailbox.resume()
    mailbox.process_messages()
    assert actor.handle_message.called


def test_suspending_in_handler_interrupts_processing(actor):
    mailbox = InternalMailbox(Mock(), actor, throughput=5)
    actor.handle_message.side_effect = lambda *args: mailbox.suspend()
    mailbox.enqueue(Mock())
    mailbox.enqueue(Mock())
    mailbox.process_messages()
    assert actor.handle_message.call_count == 1


def test_closing_in_handler_interrupts_processing(actor):
    mailbox = InternalMailbox(Mock(), actor, throughput=5)
    actor.handle_system_message.side_effect = lambda *args: mailbox.close()
    mailbox.enqueue_system(Mock())
    mailbox.enqueue_system(Mock())
    mailbox.enqueue(Mock())
    mailbox.enqueue(Mock())
    mailbox.process_messages()
    assert actor.handle_system_message.call_count == 1


def test_set_scheduled_while_already_scheduled_should_fail(mailbox):
    assert mailbox.set_scheduled() is True
    assert mailbox.is_scheduled()
    assert mailbox.set_scheduled() is False


def test_sets_itself_idle_after_processing_messages(mailbox):
    mailbox.enqueue(Mock())
    mailbox.set_scheduled()
    mailbox.process_messages()
    assert mailbox.is_idle()


def test_flushing_when_open_should_raise(mailbox):
    mailbox.enqueue(Mock())
    with pytest.raises(Exception):
        mailbox.flush_messages()


def test_flushing_when_closed_should_return_user_messages_in_queue(mailbox):
    message = object()
    mailbox.enqueue(message)
    mailbox.close()
    assert mailbox.flush_messages() == [message]

