"""Regression coverage for untranslated settings and runtime source precedence."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from test_dom_translation_guards import (
    DOM_FIXTURE_PREFIX, extract_windows_dom_template,
    load_python_patcher, materialize_windows_dom_script,
)
import subprocess

ROOT = Path(__file__).resolve().parents[1]


class SettingsTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.english = json.loads((ROOT / 'tests/fixtures/settings-phrases-en.json').read_text(encoding='utf-8'))
        cls.chinese = json.loads((ROOT / 'resources/frontend-zh-CN.json').read_text(encoding='utf-8'))

    def test_settings_resource_ids_no_longer_override_chinese_defaults_with_english(self):
        for key, source in self.english.items():
            with self.subTest(source=source):
                self.assertIn(key, self.chinese)
                self.assertNotEqual(source, self.chinese[key])
                self.assertRegex(self.chinese[key], r'[\u3400-\u9fff]')

    def test_format_variables_and_rich_text_links_are_preserved(self):
        for key, source in self.english.items():
            target = self.chinese[key]
            with self.subTest(source=source):
                self.assertEqual(sorted(re.findall(r'\{[^{}]*\}', source)), sorted(re.findall(r'\{[^{}]*\}', target)))
                self.assertEqual(sorted(re.findall(r'</?\w+>', source)), sorted(re.findall(r'</?\w+>', target)))

    def test_exact_settings_overrides_are_loaded_by_python_runtime(self):
        patcher = load_python_patcher()
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            i18n = app / patcher.FRONTEND_I18N_REL
            i18n.mkdir(parents=True)
            (i18n / 'en-US.json').write_text('{}', encoding='utf-8')
            mapping = patcher.build_online_translation_map(app, 'zh-CN')
            self.assertEqual(mapping['Choose whether Claude works on all sites by default'], '选择默认是否允许 Claude 在所有网站上工作')
            self.assertEqual(mapping['Capabilities'], '功能')
            self.assertNotIn('What’s up next, {name}?', mapping)

    def test_windows_dynamic_labels_preserve_user_content_and_multiple_captures(self):
        sample = 'You’ve used ~2× more tokens than The Hobbit.'
        prefix = DOM_FIXTURE_PREFIX + '\n' + '\n'.join([
            'const stat = body.append(textElement(' + json.dumps(sample) + '));',
            'const user = body.append(textElement(' + json.dumps(sample) + ', [\'[data-testid="user-message"]\']));',
            'const example = body.append(textElement(' + json.dumps(sample) + ', ["code"], "CODE"));',
            'const usage = body.append(textElement("6% used"));',
            'const greeting = body.append(textElement("What’s up next, Jason?"));',
            'const midnight = body.append(textElement("Resets Sun 12:40 AM"));',
            'const noon = body.append(textElement("Resets Friday 12:00 PM"));',
            'const peak = body.append(textElement("10 PM"));',
            'const codeSettings = body.append(new Element("DIV", ["[data-testid*=code]"]));',
            'const dialogLabel = body.append(textElement("Save", [\'[role="dialog"]\']));',
            'const age = body.append(textElement("21 minutes ago"));',
            'const codeSettingsTitle = codeSettings.append(textElement("Settings"));',
            'const setting = body.append(textElement("Save", [\'[id^="setting-"]\']));',
        ])
        suffix = 'process.stdout.write(JSON.stringify({stat:stat.textContent,user:user.textContent,code:example.textContent,usage:usage.textContent,greeting:greeting.textContent,midnight:midnight.textContent,noon:noon.textContent,peak:peak.textContent,setting:setting.textContent,codeSettings:codeSettingsTitle.textContent,dialog:dialogLabel.textContent,age:age.textContent}));'
        script = materialize_windows_dom_script(extract_windows_dom_template())
        result = subprocess.run(['node'], input=prefix + '\n' + script + ';\n' + suffix, encoding='utf-8', text=True, capture_output=True, check=True)
        values = json.loads(result.stdout)
        self.assertEqual(values['stat'], '你使用的 Token 数约为《The Hobbit》的 2 倍。')
        self.assertEqual(values['user'], sample)
        self.assertEqual(values['code'], sample)
        self.assertEqual(values['usage'], '已使用 6%')
        self.assertEqual(values['greeting'], 'Jason，接下来做什么？')
        self.assertEqual(values['midnight'], '于 周日 0:40 重置')
        self.assertEqual(values['noon'], '于 周五 12:00 重置')
        self.assertEqual(values['peak'], '22 时')
        self.assertEqual(values['setting'], '保存')
        self.assertEqual(values['codeSettings'], '设置')
        self.assertEqual(values['dialog'], '保存')
        self.assertEqual(values['age'], '21 分钟前')


if __name__ == '__main__':
    unittest.main()
