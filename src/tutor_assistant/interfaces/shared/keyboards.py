"""Centralized ReplyKeyboardMarkup factories."""

from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

# Button label constants — shared so handlers can compare against them.
BTN_ADD_STUDENT = "Добавить ученика"
BTN_LIST_STUDENTS = "Мои ученики"
BTN_TODAY = "Сегодня"
BTN_TOMORROW = "Завтра"
BTN_UPCOMING = "На неделю"
BTN_SETTINGS = "Настройки"

BTN_SKIP = "Пропустить"
BTN_DONE = "Готово"
BTN_CONFIRM = "Подтвердить"
BTN_CANCEL_ADD = "Отменить"
BTN_DELETE_YES = "Да, удалить"
BTN_DELETE_NO = "Нет, отменить"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_ADD_STUDENT), KeyboardButton(BTN_LIST_STUDENTS)],
            [KeyboardButton(BTN_TODAY), KeyboardButton(BTN_TOMORROW), KeyboardButton(BTN_UPCOMING)],
            [KeyboardButton(BTN_SETTINGS)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_SKIP)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def done_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_DONE)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_add_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_CONFIRM), KeyboardButton(BTN_CANCEL_ADD)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_delete_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_DELETE_YES), KeyboardButton(BTN_DELETE_NO)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
