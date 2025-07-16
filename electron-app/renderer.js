const e = React.createElement;
const { useState, useEffect } = React;
const { exec, spawn } = require('child_process');
const fs = require('fs');
const YAML = require('js-yaml');

function toggleClass(el, name, add){
  if(add){ el.classList.add(name); } else { el.classList.remove(name); }
}

function InfoLabel({text, info}) {
  return e('label', {className:'col-span-1 flex items-center'}, [
    text,
    e('span', {className:'ml-1 text-blue-600 cursor-help', title: info, 'aria-label': `${text} help`}, 'ℹ️')
  ]);
}

function App() {
  const [step, setStep] = useState(0); // 0 brief, 1 pipeline, 2 run
  const [chapterWords, setChapterWords] = useState(4000);
  const [partWords, setPartWords] = useState(1500);
  const [maxTokens, setMaxTokens] = useState(16000);
  const [model, setModel] = useState('gpt-4.1');
  const [apiKey, setApiKey] = useState('');
  const [pipelineText, setPipelineText] = useState('');
  const [savedPipeline, setSavedPipeline] = useState('');
  const [steps, setSteps] = useState([]);
  const [dragIndex, setDragIndex] = useState(null);
  const [logs, setLogs] = useState('');
  const [tokens, setTokens] = useState(0);
  const [bookPlan, setBookPlan] = useState('{}');
  const [formats, setFormats] = useState({docx:true,pdf:true,epub:true});
  const [dark, setDark] = useState(false);

  useEffect(() => {
    toggleClass(document.body, 'dark', dark);
  }, [dark]);

  function run(cmd, cb) {
    exec(cmd, (error, stdout, stderr) => {
      console.log(stdout);
      console.error(stderr);
      if (cb) cb();
    });
  }

  function runSpawn(cmd, args, cb) {
    const p = spawn(cmd, args);
    setLogs('');
    setTokens(0);
    p.stdout.on('data', d => {
      const t = d.toString();
      setLogs(x => x + t);
      const m = t.match(/TOKENS_USED=(\d+)/);
      if (m) setTokens(x => x + parseInt(m[1], 10));
    });
    p.stderr.on('data', d => setLogs(x => x + d.toString()));
    p.on('close', () => cb && cb());
  }

  function runPrebake() {
    try {
      const obj = JSON.parse(bookPlan || '{}');
      obj.output_preferences = obj.output_preferences || {};
      obj.output_preferences.file_formats = Object.keys(formats).filter(k=>formats[k]);
      fs.writeFileSync('book_plan.json', JSON.stringify(obj, null, 2));
    } catch(e) {
      fs.writeFileSync('book_plan.json', bookPlan);
    }
    run(`OPENAI_API_KEY=${apiKey} WORDS_PER_CHAPTER=${chapterWords} WORDS_PER_PART=${partWords} MAX_OUTPUT_TOKENS=${maxTokens} MODEL=${model} python -m orchestrator.agents.prebake_agent`, loadPipeline);
  }

  function buildPipeline() {
    run(`OPENAI_API_KEY=${apiKey} python orchestrator/pipeline_builder.py`, loadPipeline);
  }

  function savePipeline() {
    const data = {steps: steps.map(s => {
      const out = {...s};
      if(out.enabled === undefined || out.enabled) delete out.enabled;
      return out;
    })};
    const txt = YAML.dump(data);
    fs.writeFileSync('pipeline/pipeline.yaml', txt);
    setSavedPipeline(txt);
    setPipelineText(txt);
  }

  function runPipeline() {
    savePipeline();
    runSpawn('python', ['-m', 'orchestrator.pipeline_runner']);
  }

  function moveStepUp(i){
    const arr = [...steps];
    if(i<=0) return;
    [arr[i-1], arr[i]] = [arr[i], arr[i-1]];
    setSteps(arr);
    setPipelineText(YAML.dump({steps: arr}));
  }

  function moveStepDown(i){
    const arr = [...steps];
    if(i>=arr.length-1) return;
    [arr[i], arr[i+1]] = [arr[i+1], arr[i]];
    setSteps(arr);
    setPipelineText(YAML.dump({steps: arr}));
  }

  function toggleStep(i){
    const arr=[...steps];
    arr[i].enabled=!arr[i].enabled;
    setSteps(arr);
    setPipelineText(YAML.dump({steps:arr}));
  }

  function handleDragStart(i){
    setDragIndex(i);
  }

  function handleDrop(i){
    if(dragIndex===null || dragIndex===i) return;
    const arr=[...steps];
    const [moved]=arr.splice(dragIndex,1);
    arr.splice(i,0,moved);
    setDragIndex(null);
    setSteps(arr);
    setPipelineText(YAML.dump({steps:arr}));
  }

  function handleDragOver(ev){
    ev.preventDefault();
  }

  function loadPipeline() {
    try {
      const txt = fs.readFileSync('pipeline/pipeline.yaml', 'utf-8');
      setPipelineText(txt);
      setSavedPipeline(txt);
      try {
        const data = YAML.load(txt);
        const loaded = (data.steps || []).map(s => ({enabled: true, ...s}));
        setSteps(loaded);
      } catch (e) {
        setSteps([]);
      }
    } catch (e) {
      setPipelineText('');
      setSavedPipeline('');
      setSteps([]);
    }
  }

  useEffect(loadPipeline, []);

  const briefStep = e('div', {className:'space-y-2'},
    e('div', {className:'grid grid-cols-2 gap-2 max-w-md'},
      e(InfoLabel, {text:'Words per Chapter', info:'Approximate target length for each chapter'}, null),
      e('input', {className:'border p-1', value: chapterWords, onChange: ev => setChapterWords(ev.target.value), 'aria-label':'Words per Chapter'}),
      e(InfoLabel, {text:'Words per Part', info:'Section length before a new pipeline part is created'}, null),
      e('input', {className:'border p-1', value: partWords, onChange: ev => setPartWords(ev.target.value), 'aria-label':'Words per Part'}),
      e(InfoLabel, {text:'Max Output Tokens', info:'Upper limit for tokens returned by the model for each step'}, null),
      e('input', {className:'border p-1', value: maxTokens, onChange: ev => setMaxTokens(ev.target.value), 'aria-label':'Max Output Tokens'}),
      e(InfoLabel, {text:'Model', info:'Choose the GPT model used by all agents'}, null),
      e('select', {className:'border p-1', value: model, onChange: ev => setModel(ev.target.value), 'aria-label':'Model'},
        e('option', {value:'gpt-4o'}, 'GPT-4o'),
        e('option', {value:'gpt-4.1'}, 'GPT-4.1')
      ),
      e(InfoLabel, {text:'OpenAI API Key', info:'Your personal API key stays local; used to call OpenAI'}, null),
      e('input', {className:'border p-1', type:'password', value: apiKey, onChange: ev => setApiKey(ev.target.value), 'aria-label':'API Key'})
    ),
    e('div', {className:'grid grid-cols-3 gap-2 max-w-md'},
      e(InfoLabel, {text:'Output Formats', info:'Choose exported book formats'}, null),
      e('label', {className:'flex items-center'}, [
        e('input', {type:'checkbox', checked:formats.docx, onChange:()=>setFormats({...formats,docx:!formats.docx}), className:'mr-1', 'aria-label':'DOCX'}),
        'DOCX'
      ]),
      e('label', {className:'flex items-center'}, [
        e('input', {type:'checkbox', checked:formats.pdf, onChange:()=>setFormats({...formats,pdf:!formats.pdf}), className:'mr-1', 'aria-label':'PDF'}),
        'PDF'
      ]),
      e('label', {className:'flex items-center col-start-2'}, [
        e('input', {type:'checkbox', checked:formats.epub, onChange:()=>setFormats({...formats,epub:!formats.epub}), className:'mr-1', 'aria-label':'EPUB'}),
        'EPUB'
      ])
    ),
    e('div', null,
      e(InfoLabel, {text:'Book Plan (JSON)', info:'Paste or edit the complete book plan used for pipeline generation'}, null),
      e('textarea', {className:'border w-full h-32 p-1', value: bookPlan, onChange: ev => setBookPlan(ev.target.value), 'aria-label':'Book Plan'})
    ),
    e('button', {className:'bg-blue-500 text-white px-3 py-1', onClick: () => {runPrebake(); setStep(1);}}, 'Run Pre-bake')
  );

  function moveStep(offset){
    setStep(s => Math.min(2, Math.max(0, s + offset)));
  }

  const pipelineList = e('ul', {className:'border p-2 max-w-md space-y-1'},
    steps.map((s, i) =>
      e('li', {
          key:i,
          className:'flex items-center justify-between p-1 bg-white rounded shadow',
          draggable:true,
          onDragStart:()=>handleDragStart(i),
          onDragOver:handleDragOver,
          onDrop:()=>handleDrop(i)
        }, [
        e('span', null, s.id || `step${i+1}`),
        e('span', null,
          e('input', {
            type:'checkbox',
            checked:s.enabled!==false,
            onChange:()=>toggleStep(i),
            className:'mr-2',
            'aria-label':'Enable Step'
          })
        ),
        e('span', null, [
          e('button', {onClick:() => moveStepUp(i), 'aria-label':'Move Up'}, '⬆️'),
          e('button', {onClick:() => moveStepDown(i), 'aria-label':'Move Down'}, '⬇️')
        ])
      ])
    )
  );

  const diffPane = e('div', {className:'grid grid-cols-2 gap-2'},[
    e('textarea', {className:'border w-full h-48 p-2', value: savedPipeline, readOnly:true, 'aria-label':'Saved Pipeline'}),
    e('textarea', {className:'border w-full h-48 p-2', value: pipelineText, onChange: ev => setPipelineText(ev.target.value), 'aria-label':'Edited Pipeline'})
  ]);

  const pipelineStep = e('div', {className:'space-y-2'},
    pipelineList,
    diffPane,
    e('div', {className:'space-x-2'},
      e('button', {className:'bg-green-500 text-white px-3 py-1', onClick: buildPipeline}, 'Build Pipeline'),
      e('button', {className:'bg-gray-500 text-white px-3 py-1', onClick: savePipeline}, 'Save Pipeline'),
      e('button', {className:'bg-purple-600 text-white px-3 py-1', onClick: () => {runPipeline(); setStep(2);}}, 'Run Pipeline')
    )
  );

  const runStep = e('div', null,
    e('pre', {className:'border p-2 overflow-auto h-40', 'aria-label':'Logs'}, logs),
    e('div', {className:'w-full bg-gray-200 h-4'},
      e('div', {
        className:'bg-green-500 h-4',
        style:{width:`${Math.min(100, tokens/maxTokens*100)}%`}
      })
    ),
    e('p', null, `Tokens used: ${tokens} / ${maxTokens} (${Math.round(tokens/maxTokens*100)}%)`)
  );

  return e('div', {className:'space-y-4'},
    e('h1', {className:'text-xl font-bold'}, 'BookGen UI'),
    e('div', {className:'space-x-2'},
      e('button', {onClick: () => setDark(d => !d), 'aria-label':'Toggle Theme'}, dark ? 'Light' : 'Dark'),
      e('button', {onClick: () => moveStep(-1), disabled: step===0}, 'Prev'),
      e('button', {onClick: () => moveStep(1), disabled: step===2}, 'Next')
    ),
    step===0 ? briefStep : step===1 ? pipelineStep : runStep
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(e(App));
