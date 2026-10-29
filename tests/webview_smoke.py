"""Teste integrado opcional no motor web real: python -m tests.webview_smoke vídeo.mp4 [vídeo.webm]."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import config as config_module
from config import default_config, load_config
from logic import ChapterManager, SubtitleManager
from web_app import WebApi
from web_backend import EditorSession, MediaServer

WORKFLOW = r"""
async function check(condition, message) { if (!condition) throw Error(message); }
const wait = async (predicate) => {
    for(let i=0;i<150;i++) { if(predicate()) return; await new Promise(resolve=>setTimeout(resolve,100)); }
    throw Error('Tempo limite de espera');
};
await wait(()=>typeof bridge !== 'undefined' && bridge && state.name && video.readyState>=2);
video.muted=true; await video.play(); await wait(()=>video.currentTime>.2); video.pause();
seekTo(1); await wait(()=>Math.abs(video.currentTime-1)<.2 && !video.seeking);
await check(video.videoWidth>0 && video.duration>0,'Sem vídeo decodificado');
$('settings').click();
await check($('settings-dialog').open,'Configurações não abriram');
$('button-jump').value='7'; $('scroll-jump').value='3';
$('video-scroll-jump').value='2'; $('track-scroll-jump').value='4';
$('cancel-settings').click();
await check(settings.small_jump===5 && settings.large_jump===20,'Cancelar alterou os saltos');
await check(settings.video_scroll_jump===5 && settings.track_scroll_jump===20,'Cancelar alterou saltos por área');
$('settings').click();
$('button-jump').value='0';
await check(!$('settings-form').checkValidity(),'Salto zero aceito');
$('button-jump').value='7'; $('scroll-jump').value='3';
$('video-scroll-jump').value='2'; $('track-scroll-jump').value='4';
const nativeSaveSettings=bridge.save_settings;
bridge.save_settings=async()=>{throw Error('Falha simulada');};
$('settings-form').requestSubmit();
await wait(()=>!savingSettings);
await check($('settings-dialog').open && $('settings-error').textContent.includes('Falha simulada') && settings.small_jump===5,'Erro não preservou edição e saltos');
bridge.save_settings=nativeSaveSettings;
$('settings-form').requestSubmit();
await wait(()=>!savingSettings);
await check(!$('settings-dialog').open && $('back-label').textContent==='7s','Salto não aplicado');
seekTo(1); $('forward').click(); await check(Math.abs(video.currentTime-8)<.2,'Avanço não usa configuração');
$('back').click(); await check(Math.abs(video.currentTime-1)<.2,'Retrocesso não usa configuração');
$('seek').dispatchEvent(new WheelEvent('wheel',{deltaY:-120,cancelable:true}));
await check(Math.abs(video.currentTime-4)<.2,'Scroll não usa configuração');
$('seek').dispatchEvent(new WheelEvent('wheel',{deltaY:120,cancelable:true}));
await check(Math.abs(video.currentTime-1)<.2,'Scroll reverso não usa configuração');
for (const [id,jump] of [['video',2],['subtitle',2],['chapter-track',4],['ruler',4]]) {
  seekTo(1);
  $(id).dispatchEvent(new WheelEvent('wheel',{deltaY:-120,bubbles:true,cancelable:true}));
  await check(Math.abs(video.currentTime-(1+jump))<.2,`Scroll em ${id} não usa o salto próprio`);
  $(id).dispatchEvent(new WheelEvent('wheel',{deltaY:120,bubbles:true,cancelable:true}));
  await check(Math.abs(video.currentTime-1)<.2,`Scroll reverso em ${id} falhou`);
  $(id).dispatchEvent(new WheelEvent('wheel',{deltaY:0,deltaX:120,bubbles:true,cancelable:true}));
  await check(Math.abs(video.currentTime-1)<.2,`Scroll horizontal em ${id} alterou o tempo`);
}
seekTo(0); $('video').dispatchEvent(new WheelEvent('wheel',{deltaY:120,bubbles:true,cancelable:true}));
await check(video.currentTime===0,'Scroll ultrapassou o início do vídeo');
seekTo(video.duration-1); $('chapter-track').dispatchEvent(new WheelEvent('wheel',{deltaY:-120,bubbles:true,cancelable:true}));
await check(video.currentTime===video.duration,'Scroll ultrapassou o fim do vídeo');
seekTo(1);
$('settings').click();
await check($('button-jump').value==='7' && $('scroll-jump').value==='3','Reabertura perdeu preferências');
await check($('video-scroll-jump').value==='2' && $('track-scroll-jump').value==='4','Reabertura perdeu saltos por área');
$('settings-dialog').querySelector('summary').click();
await check($('settings-dialog').querySelector('details').open && $('key-short').textContent,'Atalhos indisponíveis');
$('settings-dialog').dispatchEvent(new Event('cancel',{cancelable:true}));
await check(!$('settings-dialog').open,'Escape não fechou configurações');
$('add-options').click();
await check($('action-menu').matches(':popover-open'),'Menu de criação não abriu');
await check($('action-menu').querySelector('[data-action=child]').disabled,'Subcapítulo habilitado sem pai');
$('action-menu').querySelector('[data-action=new]').click(); let form=$('edit-form');
await check(form.elements.title.value==='Capítulo 1','Título padrão ausente');
await check(form.elements.title.selectionStart===0 && form.elements.title.selectionEnd===10,'Título padrão não selecionado');
const timeInput=form.elements.start;
timeInput.focus(); timeInput.value='1234'; timeInput.setSelectionRange(4,4);
timeInput.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:'1234'}));
await check(timeInput.value==='00:12:34' && timeInput.selectionStart===8,'Máscara não formata números');
timeInput.value='99'; timeInput.setSelectionRange(2,2); timeInput.dispatchEvent(new InputEvent('input',{bubbles:true}));
await check(!timeInput.checkValidity(),'Máscara aceitou segundos inválidos');
const pastedTime=new DataTransfer(); pastedTime.setData('text/plain','01:02:03');
timeInput.dispatchEvent(new ClipboardEvent('paste',{bubbles:true,cancelable:true,clipboardData:pastedTime}));
await check(timeInput.value==='01:02:03' && timeInput.checkValidity(),'Colagem de tempo formatado falhou');
$('fields').querySelector('[data-capture=start]').click();
await check(timeInput.value==='00:00:01','Tempo atual não respeitou a máscara');
timeInput.focus(); timeInput.value='00:12:34'; timeInput.setSelectionRange(3,5); timeInput.setRangeText('45',3,5,'end');
timeInput.dispatchEvent(new InputEvent('input',{bubbles:true}));
await check(timeInput.value==='00:45:34' && timeInput.selectionStart===6,'Edição dos minutos perdeu o cursor');
form.elements.title.value='Abertura';
form.elements.start.value='00:00'; form.elements.end.value='00:05';
await saveEditor({preventDefault(){}});
await check(items().length===1 && !$('editor-dialog').open,'Capítulo não salvo');
const firstRow=document.querySelector('.record-select');
firstRow.click(); await check(firstRow.isConnected,'Seleção recriou o alvo do duplo clique');
firstRow.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));
await check($('editor-dialog').open && form.elements.title.value==='Abertura','Duplo clique não abriu a edição correta');
$('cancel-dialog').click();
$('add-options').click(); $('action-menu').querySelector('[data-action=child]').click();
await check(form.elements.title.value==='Subcapítulo 1','Título padrão de filho ausente');
form.elements.title.value='Detalhe';
form.elements.start.value='00:02'; form.elements.end.value='00:08';
await saveEditor({preventDefault(){}});
await check(items()[0].end===8 && items()[0].subs.length===1,'Hierarquia não expandida');
document.querySelectorAll('.record-menu')[1].click();
await check($('action-menu').querySelector('[data-action=edit]') && $('action-menu').querySelector('[data-action=remove]'),'Ações do capítulo ausentes');
$('action-menu').querySelector('[data-action=edit]').click();
await check(form.elements.title.value==='Detalhe','Menu editou outro capítulo'); $('cancel-dialog').click();
document.querySelectorAll('.record-menu')[1].click(); $('action-menu').querySelector('[data-action=child]').click();
form.elements.title.value='Subdetalhe';
form.elements.start.value='00:01'; form.elements.end.value='00:09';
await saveEditor({preventDefault(){}});
await check($('editor-dialog').open && $('form-error').textContent.length>0,'Intervalo inválido aceito');
form.elements.start.value='00:03'; await saveEditor({preventDefault(){}});
await check(items()[0].subs[0].subs.length===1,'Nova tentativa duplicou ou perdeu item');
await check(document.querySelectorAll('.timeline-row').length===1,'Descendentes devem compartilhar a faixa do pai');
const bars=[...document.querySelectorAll('.timeline-lane button')];
await check(bars.length===3,'Linha do tempo não inclui descendentes');
const bounds=bars.map(bar=>bar.getBoundingClientRect());
await check(bounds.every(rect=>Math.abs(rect.top-bounds[0].top)<1),'Descendentes não estão sobrepostos ao pai');
await check(bars.map(bar=>bar.textContent).join('|')==='Abertura|Detalhe|Subdetalhe','Hierarquia das camadas incorreta');
await check(bars.every((bar,index)=>Number(bar.style.zIndex)===index+1),'Filhos devem ser desenhados acima dos pais');
await check(bounds[1].left>=bounds[0].left && bounds[1].right<=bounds[0].right+1,'Filho fora do pai');
await check(Math.abs(parseFloat(bars[0].style.width)-9/video.duration*100)<.01,'Duração perdeu proporcionalidade');
await check(Math.abs(parseFloat(bars[1].style.left)-2/video.duration*100)<.01,'Início perdeu proporcionalidade');
bars[1].click(); await check(Math.abs(video.currentTime-2)<.1,'Barra não navega até o capítulo');
showEditor(); await check(form.elements.title.value==='Subcapítulo 1','Título padrão de irmão incorreto'); $('cancel-dialog').click();
document.querySelector('.record-select').click(); $('add').click();
await check(form.elements.title.value==='Capítulo 1','Título padrão da raiz incorreto');
form.elements.end.value='00:10'; await saveEditor({preventDefault(){}});
await check(document.querySelectorAll('.timeline-row').length===2,'Capítulos principais simultâneos devem usar faixas distintas');
const savedTimeline=structuredClone(state.data.chapters);
state.data.chapters=[{id:'a',title:'A',start:0,end:4,subs:[{id:'a.1',title:'A.1',start:1,end:3,subs:[]}]},
 {id:'b',title:'B',start:2,end:8,subs:[]},{id:'c',title:'C',start:4,end:12,subs:[]}];
renderTimeline();
const timelineLanes=[...document.querySelectorAll('.timeline-lane')];
await check(timelineLanes.length===2 && timelineLanes[0].querySelector('[data-chapter-id=c]') && timelineLanes[0].querySelector('[data-chapter-id=a]'),'Capítulos sem sobreposição não reutilizam a faixa');
await check(timelineLanes[0].querySelector('[data-chapter-id="a.1"]'),'Filho separado do pai');
state.data.chapters=savedTimeline; renderTimeline();
const countBeforeDelete=items().length;
showEditor(); await check(form.elements.title.value==='Capítulo 2','Título padrão duplicado'); $('cancel-dialog').click();
const nativeConfirm=window.confirm; window.confirm=()=>true;
document.querySelector('.record.selected .record-menu').click(); $('action-menu').querySelector('[data-action=remove]').click();
await wait(()=>!busy); window.confirm=nativeConfirm;
await check(items().length===countBeforeDelete-1,'Exclusão pelo menu não foi salva');
tab='subtitles'; selected=null; render(); showEditor();
form.elements.text.value='Legenda de teste <b>literal</b>'; form.elements.start.value='00:00.125'; form.elements.end.value='00:04.125';
await saveEditor({preventDefault(){}}); seekTo(1); updatePlayback();
await check($('subtitle').textContent==='Legenda de teste <b>literal</b>','Legenda não sincronizada');
seekTo(6); updatePlayback(); await check($('subtitle').textContent==='','Legenda fora do intervalo');
tab='casting'; selected=null; render(); showEditor(); form.elements.name.value='Pessoa de teste'; await saveEditor({preventDefault(){}});
tab='metadata'; selected=null; render(); showEditor(); form.elements.key.value='Local'; form.elements.value.value='Brasil'; await saveEditor({preventDefault(){}});
selected=items()[0].id; showEditor('child'); form.elements.key.value='País'; await saveEditor({preventDefault(){}});
await check(items()[0].value==='' && items()[0].children[0].value==='Brasil','Valor não transferido para folha');
tab='images'; selected=null; render(); showEditor(); form.elements.title.value='Imagem sintética';
let canvas=document.createElement('canvas'); canvas.width=120; canvas.height=80;
canvas.getContext('2d').fillRect(0,0,120,80);
let blob=await new Promise(resolve=>canvas.toBlob(resolve));
const unsupportedHeader=new Uint8Array([0,0,0,24,102,116,121,112,97,118,105,102]);
await loadImage(new File([unsupportedHeader],'renomeada.jpg',{type:'image/jpeg'}));
await check(!cropImage && $('form-error').textContent.includes('Formato não suportado'),'AVIF renomeado não foi recusado antes da decodificação');
const bmpHeader=new Uint8Array([66,77,0,0,0,0,0,0,0,0,0,0]);
await loadImage(new File([bmpHeader],'renomeada.png',{type:'image/png'}));
await check(!cropImage && $('form-error').textContent.includes('Formato não suportado'),'BMP renomeado não foi recusado');
for(const type of ['image/jpeg','image/png','image/webp']) {
    const sample=await new Promise(resolve=>canvas.toBlob(resolve,type));
    await loadImage(new File([sample],'amostra',{type}));
    await check(!!cropImage,`Formato permitido recusado: ${type}`);
}
const gifBytes=Uint8Array.from(atob('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'),c=>c.charCodeAt(0));
await loadImage(new File([gifBytes],'amostra.gif',{type:'image/gif'}));
await check(!!cropImage,'GIF foi recusado');
await loadImage(new File([blob],'amostra.png',{type:'image/png'}));
$('crop-ratio').value='1'; $('crop-zoom').value='2'; drawCrop();
await saveEditor({preventDefault(){}});
await check(items().length===1 && items()[0].width===40 && items()[0].height===40,'Recorte não persistido');
tab='casting'; selected=items()[0].id; render(); showEditor('edit');
form.querySelector('input[name=images]').checked=true; await saveEditor({preventDefault(){}});
await check(items()[0].images.length===1,'Associação não persistida');
$('search').value='ausente'; render(); await check(!document.querySelector('.record'),'Filtro não aplicado');
$('search').value=''; tab='chapters'; selected=items()[0].id; render();
$('library').click(); await wait(()=>!libraryBusy);
await check($('library-dialog').open && libraryEntries.length===1,'Biblioteca não lista o vídeo salvo');
$('library-search').value='ausente'; $('library-search').dispatchEvent(new Event('input'));
await check(!$('library-records').querySelector('[data-history-id]'),'Busca da biblioteca não filtrou');
$('library-search').value=''; $('library-search').dispatchEvent(new Event('input'));
const nativeOpenHistory=bridge.open_history;
bridge.open_history=async()=>{throw Error('Arquivo indisponível');};
$('library-records').querySelector('button').click(); await wait(()=>!libraryBusy);
await check($('library-dialog').open && $('library-error').textContent.includes('indisponível'),'Falha de abertura não foi exibida');
bridge.open_history=nativeOpenHistory;
$('library-records').querySelector('button').click(); await wait(()=>!libraryBusy);
await check(!$('library-dialog').open && state.name,'Biblioteca não reabriu o vídeo');
await wait(()=>video.readyState>=2);
return {duration:video.duration,width:video.videoWidth,height:video.videoHeight,chapters:flatten(items()).length,
        subtitle:state.subtitles[0], image:state.data.images[0].width};
"""


def evaluate_async(window: Any, source: str) -> Any:
    """Executa um cenário assíncrono e propaga falhas do JavaScript ao teste Python."""
    window.evaluate_js(
        "window.__smoke={done:false}; (async()=>{" + source + "})()"
        ".then(result=>window.__smoke={done:true,result})"
        ".catch(error=>window.__smoke={done:true,error:String(error.stack||error)}); null"
    )
    for _ in range(400):
        result = window.evaluate_js("window.__smoke")
        if result and result.get("done"):
            if result.get("error"):
                raise AssertionError(result["error"])
            return result.get("result")
        time.sleep(0.1)
    raise TimeoutError("O cenário integrado não terminou em 40 segundos.")


def main() -> None:
    """Abre amostras copiadas para uma pasta temporária e valida o fluxo real de edição."""
    import webview

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", nargs="+", type=Path)
    args = parser.parse_args()
    failures: list[Exception] = []
    with tempfile.TemporaryDirectory(prefix="chapter_webview_") as directory:
        config_module.CONFIG_PATH = Path(directory) / "config.vdb"
        samples = []
        for index, path in enumerate(args.videos):
            target = Path(directory) / f"amostra_{index}{path.suffix}"
            shutil.copyfile(path, target)
            samples.append(target)
        session = EditorSession()
        session.open(str(samples[0]))
        server = MediaServer(session)
        api = WebApi(session, default_config())
        window = webview.create_window(
            "Validação WebView2 — Editor de Capítulos",
            server.start(),
            js_api=api,
            width=1440,
            height=900,
            min_size=(600, 500),
        )
        api._window = window

        def run() -> None:
            """Verifica o frontend e confirma os dados com os leitores da interface clássica."""
            try:
                window.events.loaded.wait(15)
                result = evaluate_async(window, WORKFLOW)
                assert load_config()["small_jump"] == 7 and load_config()["large_jump"] == 3
                assert load_config()["video_scroll_jump"] == 2 and load_config()["track_scroll_jump"] == 4
                print("FLUXO:", json.dumps(result, ensure_ascii=False), flush=True)
                data = ChapterManager(str(samples[0])).load()
                assert data["chapters"][0]["end"] == 9
                assert data["casting"][0]["images"] == [data["images"][0]["id"]]
                assert SubtitleManager(str(samples[0])).load()[0]["start"] == 125
                for width, height in [(1440, 900), (1024, 768), (860, 620), (640, 700)]:
                    window.resize(width, height)
                    time.sleep(0.3)
                    layout = window.evaluate_js(
                        "({width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,"
                        "controls:[...document.querySelectorAll('.play-buttons button,.audio button')]"
                        ".every(e=>e.getBoundingClientRect().right<=innerWidth)})"
                    )
                    assert not layout["overflow"] and layout["controls"], layout
                    menu_layout = evaluate_async(
                        window,
                        """
                        $('add-options').click();
                        const rect=$('action-menu').getBoundingClientRect();
                        const fits=rect.left>=0 && rect.right<=innerWidth && rect.top>=0 && rect.bottom<=innerHeight;
                        $('action-menu').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
                        if($('action-menu').matches(':popover-open') || !fits) throw Error('Menu fora da janela ou Escape falhou');
                        return fits;
                    """,
                    )
                    assert menu_layout
                    settings_layout = evaluate_async(
                        window,
                        """
                        $('settings').click();
                        $('settings-dialog').querySelector('details').open=true;
                        const dialog=$('settings-dialog');
                        const rect=dialog.getBoundingClientRect();
                        const fits=rect.left>=0 && rect.right<=innerWidth && rect.top>=0 && rect.bottom<=innerHeight
                            && dialog.scrollWidth<=dialog.clientWidth;
                        $('close-settings').click();
                        if(!fits) throw Error('Configurações fora da janela');
                        return fits;
                        """,
                    )
                    assert settings_layout
                    library_layout = evaluate_async(
                        window,
                        """
                        $('library').click();
                        for(let i=0;i<100 && libraryBusy;i++) await new Promise(r=>setTimeout(r,50));
                        const dialog=$('library-dialog');
                        const rect=dialog.getBoundingClientRect();
                        const fits=rect.left>=0 && rect.right<=innerWidth && rect.top>=0 && rect.bottom<=innerHeight
                            && dialog.scrollWidth<=dialog.clientWidth;
                        $('close-library').click();
                        if(!fits) throw Error('Biblioteca fora da janela');
                        return fits;
                        """,
                    )
                    assert library_layout
                    print("LAYOUT:", width, height, layout, flush=True)
                for path in samples[1:]:
                    snapshot = session.open(str(path))
                    window.evaluate_js("accept(" + json.dumps(snapshot) + ",true)")
                    result = evaluate_async(
                        window,
                        """
                        for(let i=0;i<100 && video.readyState<2;i++) await new Promise(r=>setTimeout(r,100));
                        video.muted=true; await video.play(); await new Promise(r=>setTimeout(r,400));
                        video.pause(); if(!video.currentTime || !video.videoWidth) throw Error('Falha de reprodução');
                        seekTo(1); return {name:state.name,width:video.videoWidth,duration:video.duration};
                    """,
                    )
                    print("MÍDIA:", json.dumps(result), flush=True)
            except Exception as exc:  # noqa: BLE001 - Repassa ao processo principal as falhas da thread de teste.
                failures.append(exc)
                print("FALHA:", repr(exc), flush=True)
            finally:
                window.confirm_close = False
                window.destroy()

        try:
            webview.start(run, gui="edgechromium" if sys.platform == "win32" else None)
        finally:
            server.close()
    if failures:
        raise failures[0]
    print("Teste integrado concluído.")


if __name__ == "__main__":
    main()
