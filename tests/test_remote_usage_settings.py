"""Check online settings copy, amounts/dates, and content protection."""
import json
import subprocess
import shutil
import unittest
from pathlib import Path

from test_dom_translation_guards import (
    DOM_FIXTURE_PREFIX, extract_windows_dom_template, materialize_windows_dom_script,
)

ROOT = Path(__file__).resolve().parents[1]


class RemoteUsageSettingsTests(unittest.TestCase):
    def test_refreshing_an_installed_patch_preserves_both_callback_shapes(self):
        shell = shutil.which('pwsh') or shutil.which('powershell')
        self.assertIsNotNone(shell, 'PowerShell is required for this Windows regression')
        source = str(ROOT / 'scripts/install_windows.ps1').replace("'", "''")
        ps = r'''
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('__SOURCE__',[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Parse error'}
foreach($fn in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)){
 if($fn.Name -in @('Remove-ExistingOnlineDomTranslationPatch','Find-OnlineDomTranslationHook')){. ([scriptblock]::Create($fn.Extent.Text))}
}
$OnlineLocaleMainMarker='__claudeZhOnlineLocaleMain'
$literal='(()=>{const quote="sample";const braces="{}";})()' | ConvertTo-Json -Compress
$results=foreach($wrapped in @($false,$true)){
 $open=if($wrapped){'(()=>{'}else{'()=>{'}
 $close=if($wrapped){'}))'}else{'})'}
 $base='ready("main_view_dom_ready")'
 $original='win.webContents.on("dom-ready",'+$open+$base+$close+';'
 $injected='win.webContents.on("dom-ready",'+$open+$base+';win.webContents.executeJavaScript('+$literal+').catch(()=>{})'+$close+';/*__claudeZhOnlineLocaleMain*/'
 $found=Find-OnlineDomTranslationHook $injected -Quiet
 $removed=Remove-ExistingOnlineDomTranslationPatch $injected
 $restored=Find-OnlineDomTranslationHook $removed.Text -Quiet
 [pscustomobject]@{FoundInjected=$found.Success;Removed=$removed.Removed;OriginalPreserved=($removed.Text -ceq $original);FoundRestored=$restored.Success}
}
$results | ConvertTo-Json -Compress
'''.replace('__SOURCE__', source)
        result = subprocess.run([shell, '-NoProfile', '-Command', ps], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', check=True)
        cases = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(len(cases), 2)
        for case in cases:
            self.assertTrue(all(case.values()), case)

    def test_remote_and_credit_settings_and_dynamic_values(self):
        overrides = json.loads((ROOT / 'resources/online-dom-zh-CN.json').read_text(encoding='utf-8'))
        mapping = dict(overrides['global'])
        sources = [
            'Use this computer from your phone and claude.ai',
            'Keep this computer awake for Remote Control',
            'Keeps this computer from going to sleep on its own. If it does go to sleep, it isn’t reachable until it wakes up.',
            'Show folders', 'Limit resets', 'No resets right now',
            'When you get one, it shows up here with its expiry date.',
            'Cloud session credits',
            'Applies automatically to cloud sessions. After it’s used or expires, your plan’s regular usage applies.',
            'While Claude is open, sessions on your other devices can start here and can read and edit files and run commands in the folders below, following your approval settings. This computer’s name and each folder’s name, path, Git branch, and repository URL are sent to Anthropic so your devices can list them.',
        ]
        dynamic = {
            'Folders (1)': '文件夹（1）',
            'Folders (17)': '文件夹（17）',
            '0 of 1 listed': '已列出 0/1 个',
            '4 of 6 listed': '已列出 4/6 个',
            '$100 of $100 left': '剩余 $100（共 $100）',
            '$0.25 of $1,000 left': '剩余 $0.25（共 $1,000）',
            'Expires 3:59 PM GMT+8, November 5': '到期时间：11月5日 15:59（GMT+8）',
            'Expires 12:00 AM GMT-4, January 1, 2027': '到期时间：2027年1月1日 0:00（GMT-4）',
            'Expires 12:00 PM GMT+5:30, May 9': '到期时间：5月9日 12:00（GMT+5:30）',
        }
        for source in sources:
            self.assertIn(source, mapping)
            self.assertRegex(mapping[source], r'[\u3400-\u9fff]')
        all_sources = sources + list(dynamic)
        declarations = [
            'const labels=' + json.dumps(all_sources, ensure_ascii=True) + '.map(s=>body.append(textElement(s)));',
            'const privateText=body.append(textElement("Expires 3:59 PM GMT+8, November 5", [\'[data-testid="user-message"]\']));',
            'const code=body.append(textElement("$100 of $100 left", ["code"], "CODE"));',
        ]
        script = materialize_windows_dom_script(extract_windows_dom_template())
        script = script.replace('M={"Settings":"设置","deploy-command":"部署命令"}', 'M=' + json.dumps(mapping, ensure_ascii=False, separators=(',', ':')))
        suffix = 'process.stdout.write(JSON.stringify({labels:labels.map(e=>e.textContent),user:privateText.textContent,code:code.textContent}));'
        result = subprocess.run(['node'], input=DOM_FIXTURE_PREFIX + '\n' + '\n'.join(declarations) + '\n' + script + ';\n' + suffix,
                                encoding='utf-8', text=True, capture_output=True, check=True)
        actual = json.loads(result.stdout)
        self.assertEqual(actual['labels'], [mapping[s] for s in sources] + list(dynamic.values()))
        self.assertEqual(actual['user'], 'Expires 3:59 PM GMT+8, November 5')
        self.assertEqual(actual['code'], '$100 of $100 left')


if __name__ == '__main__':
    unittest.main()
