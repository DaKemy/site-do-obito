const painelEntrar = document.getElementById("EntrarPainel");
const painelCadastro = document.getElementById("CadastroSite");
const indicador = document.getElementById("Indicador");

function mostrarEntrar() {
    painelEntrar.style.display = "grid";
    painelCadastro.style.display = "none";
    indicador.style.transform = "translateX(0)";
}

function mostrarCadastro() {
    painelEntrar.style.display = "none";
    painelCadastro.style.display = "flex";
    indicador.style.transform = "translateX(100%)";
}







const campoAcesso = document.getElementById("loginAcesso");

document.getElementById("formEntrar").addEventListener("submit", function(event) {

    const valor = campoAcesso.value.trim();

    // Verifica se é um email válido
    const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor);

    // Verifica se é um telefone brasileiro com DDD
    const telefoneValido = /^\(?\d{2}\)?\s?9?\d{4}-?\d{4}$/.test(valor);

    if (!emailValido && !telefoneValido) {
        event.preventDefault();
        alert("Digite um email ou telefone válido!");
        campoAcesso.focus();
    }

});
