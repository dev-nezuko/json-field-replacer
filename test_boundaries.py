import json
from pathlib import Path
import subprocess
import sys
import pytest
from substitute import substitution

def test_depth_zero_preserves_dictionary_identity_and_values():
    original={'nested':{'value':3},'value':1}
    assert substitution(original,0) is original
    assert original=={'nested':{'value':3},'value':1}

def test_depth_one_only_wraps_root_leaves():
    assert substitution({'root':1,'nested':{'value':2}},1)=={'root':{'_content':1,'_type':"<class 'int'>"},'nested':{'value':2}}

def test_lists_are_whole_leaf_values_and_types_are_python_names():
    result=substitution({'items':[{'value':1}],'ready':True,'empty':None})
    assert result['items']=={'_content':[{'value':1}],'_type':"<class 'list'>"}
    assert result['ready']['_type']=="<class 'bool'>"
    assert result['empty']['_type']=="<class 'NoneType'>"

@pytest.mark.parametrize('value',[[],None,42])
def test_root_must_be_an_object(value):
    with pytest.raises(TypeError):substitution(value)

@pytest.mark.parametrize('depth',[-1,'one',True])
def test_invalid_depth_is_rejected(depth):
    with pytest.raises(ValueError):substitution({},depth)

def test_invalid_input_does_not_truncate_existing_output(tmp_path):
    source=tmp_path/'input.json';source.write_text('{broken')
    output=tmp_path/'output.json';output.write_text('keep-existing-output')
    result=subprocess.run([sys.executable,str(Path(__file__).with_name('substitute.py')),str(source),str(output)],capture_output=True,text=True)
    assert result.returncode==2;assert output.read_text()=='keep-existing-output'

def test_cli_preserves_legacy_depth_argument_and_unicode(tmp_path):
    source=tmp_path/'input.json';source.write_text(json.dumps({'name':'café','nested':{'value':1}}))
    output=tmp_path/'output.json'
    result=subprocess.run([sys.executable,str(Path(__file__).with_name('substitute.py')),str(source),'1',str(output)],capture_output=True,text=True)
    assert result.returncode==0
    assert json.loads(output.read_text())=={'name':{'_content':'café','_type':"<class 'str'>"},'nested':{'value':1}}
