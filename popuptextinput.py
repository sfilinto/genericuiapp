from __future__ import print_function

from kivy.core.window import Window
from kivy.uix.textinput import TextInput
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.behaviors.focus import FocusBehavior
from kivy.uix.popup import Popup
from kivy.logger import Logger
from kivy.clock import Clock

import traceback
import weakref
import functools

class FocusButton(FocusBehavior, Button):
    pass

class XTextInput(TextInput):
    def __init__(self, *a, **k):
        self.register_event_type('on_prev')
        self.register_event_type('on_next')
        self.register_event_type('on_next_suggest')
        self.register_event_type('on_accept_suggest')
        super(XTextInput, self).__init__(*a, **k)
        
    def insert_text(self, substring, from_undo=False):
        Logger.info('insert_text {} {}'.format(substring, from_undo))
        if substring == '<':
            self.dispatch('on_prev')
            return
        elif substring == '>':
            self.dispatch('on_next')
            return
        elif substring == '#':
            self.dispatch('on_accept_suggest')
            return
        elif substring == '^':
            self.dispatch('on_next_suggest')
            return

        return super(XTextInput, self).insert_text(substring, from_undo=from_undo)
    def on_prev(self, *a): pass
    def on_next(self, *a): pass
    def on_next_suggest(self, *a): pass
    def on_accept_suggest(self, *a): pass

class PopupTextInput(Button):
    title = StringProperty("")
    text = StringProperty("")
    visible = False
    def __init__(self, *a, **k):
        self.register_event_type('on_text_done')
        self.field = k.pop('field', None)
        self.titlewidget = k.pop('titlewidget', None)
        self.conn = k.pop('conn', None)
        try: self.wprevref = weakref.ref(k.pop('wprev'))
        except: self.wprevref = None
        self.wnextref = None
        super(PopupTextInput, self).__init__(*a, **k)
        try:
            title = self.titlewidget.text
        except: title = ''
        self.suggest_idx = 0
        self.popup_input = XTextInput(text=self.text, use_bubble=True, multiline=False)
        self.popup_input.bind(on_prev=self.on_previous)
        self.popup_input.bind(on_next=self.on_next)
        self.popup_input.bind(on_next_suggest=self.on_next_suggest)
        self.popup_input.bind(on_accept_suggest=self.on_accept_suggest)
        self.popup_input.bind(text=self.on_edit_text)
        self.popup = Popup(title=title,
                           size_hint=(.9, None),
                           height=300,
                           content=self.popup_input)
        self.popup.bind(on_dismiss=self.on_popup_closed)

    def set_wnext(self, wnext):
        self.wnextref = weakref.ref(wnext)

    def on_next(self, *a):
        Logger.info('on_next')
        self.hide_popup()
        _self = self
        while _self:
            wnext = None
            try:
                wnext = _self.wnextref()
                if wnext.disabled is True: raise Exception
                wnext.show_popup()
                _self = None
            except:
                traceback.print_exc()
                _self = wnext

    def on_previous(self, *a):
        Logger.info('on_previous')
        self.hide_popup()
        _self = self
        while _self:
            wprev = None
            try:
                wprev = _self.wprevref()
                if wprev.disabled is True: raise Exception
                wprev.show_popup()
                _self = None
            except:
                traceback.print_exc()
                _self = wprev

    def on_title_text(self, *a):
        Logger.info('on_title_text {}'.format(a))

    def on_press(self, *a):
        Logger.info('PopupTextInput.on_press')
        Clock.schedule_once(self.show_popup, 0)

    def show_popup(self, *a):
        self.popup_input.text = self.text
        self.popup.open()
        PopupTextInput.visible = True
        Clock.schedule_once(self.show_keyboard, 0)

    def hide_popup(self, *a):
        Logger.info('hide_popup')
        try: self.popup.dismiss()
        except: traceback.print_exc()
        PopupTextInput.visible = False

    def on_text_done(self, *a): pass

    def on_popup_closed(self, *a):
        Logger.info('on_popup_closed')
        self.dispatch('on_text_done', self.popup_input, self.popup_input.text)

    def show_keyboard(self, *a):
        keyboard = Window.request_keyboard(self._keyboard_close, self.popup_input)
        Clock.schedule_once(self.set_input_focus, 0)

    def set_input_focus(self, *a):
        self.popup_input.focus = True

    def _keyboard_close(self, *a):
        Logger.info('_keyboard_close {}'.format(a))

    def on_edit_text(self, w, text, *a):
        Logger.info('on_edit_text {} {} {}'.format(w, text, a))
        self.text = text
        
    def on_tw_text(w, value):
        Logger.info('on_tw_text {} {}'.format(w, value))
        self.popup.title = value

    def on_text(self, w, value):
        Logger.info('on_text {}'.format(value))
        try: self.popup_label.text = value
        except: pass
        
        #Clock.schedule_once(functools.partial(self.make_suggestions, value), 0)
        try: self.make_suggestions(value)
        except: traceback.print_exc()
        #return False

    def on_next_suggest(self, *a):
        Logger.info('on_next_suggest')
        if len(self.suggestions):
            self.suggest_idx += 1
            self.suggest_idx %= len(self.suggestions)
            self.show_suggestion()

    def on_accept_suggest(self, *a):
        Logger.info('on_accept_suggest')
        self.popup_input.text += self.suggestion_text
        self.suggestion_text = ""
        self.suggest_idx = 0
        self.suggestions = []
        self.show_suggestion()

    def make_suggestions(self, value, *a):
        Logger.info('make_suggestions {}'.format(value))
        self.popup_input.suggestion_text = "?"
        if len(value) == 0:
            return 
        if value[-1] == ' ':
            print('new word {}'.format(value))
            return
        words = value.split()
        self.last_word = words[-1]
        self.suggestions = self.get_suggestions(self.field, self.last_word)
        Logger.info('suggestions: {}'.format(self.suggestions))
        self.suggest_idx = 0
        self.show_suggestion()

    def show_suggestion(self, *a):
        try: suggestion_text = self.suggestion_text = self.suggestions[self.suggest_idx][len(self.last_word):]
        except IndexError: suggestion_text = ''

        if len(self.suggestions) > 1:
            suggestion_text += ' [i]{}/{}[/i]'.format(self.suggest_idx+1, len(self.suggestions))
        self.popup_input.suggestion_text = suggestion_text

    def get_suggestions(self, field, word):
        if field is None or len(word)==0:
            return []
        word_end = word[:-1] + chr(ord(word[-1])+1)
        sql = '''select word from autocomplete where field=? and word > ? and word < ? order by count limit 5'''
        cursor = self.conn.cursor()
        Logger.info('get_suggestions {} : {} {} => {}'.format(field, word, word_end, sql))
        return [ r[0] for r in cursor.execute(sql, (field, word, word_end)) ]
