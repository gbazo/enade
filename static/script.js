// Banco de dados das questões (normalmente viria do backend)
const allQuestions = [];

// Array para armazenar os questionários criados
let savedQuestionnaires = JSON.parse(localStorage.getItem('savedQuestionnaires')) || [];

// Questionário em criação
let currentQuestionnaire = null;

// Carregar as questões a partir de um JSON
fetch('questions.json')
    .then(response => response.json())
    .then(data => {
        // Adicionar questões ao array
        allQuestions.push(...data);
        
        // Renderizar todas as questões
        renderAllQuestions();
    })
    .catch(error => {
        console.error('Erro ao carregar as questões:', error);
    });

// Função para abrir abas
function openTab(tabElement, tabId) {
    const tabContents = document.getElementsByClassName("tab-content");
    for (let i = 0; i < tabContents.length; i++) {
        tabContents[i].classList.remove("active");
    }
    
    const tabs = document.getElementsByClassName("tab");
    for (let i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove("active");
    }
    
    document.getElementById(tabId).classList.add("active");
    tabElement.classList.add("active");
    
    // Se a aba de questionários salvos foi aberta, atualizar a lista
    if (tabId === 'tab-saved') {
        renderSavedQuestionnaires();
    }
    
    // Se a aba de respostas foi aberta, carregar respostas e preencher o filtro
    if (tabId === 'tab-responses') {
        populateQuestionnaireFilter();
        loadResponses();
    }
}

// Função para renderizar todas as questões
function renderAllQuestions() {
    const container = document.getElementById('all-questions-container');
    container.innerHTML = '';
    
    allQuestions.forEach(question => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-item';
        questionDiv.dataset.id = question.id;
        questionDiv.dataset.category = question.category;
        questionDiv.dataset.type = question.type;
        
        let optionsHtml = '';
        if (question.type === 'multiple-choice') {
            optionsHtml = `<div class="question-options">`;
            question.options.forEach(option => {
                optionsHtml += `<div><strong>${option.label})</strong> ${option.text}</div>`;
            });
            optionsHtml += `</div>`;
        } else if (question.type === 'likert') {
            optionsHtml = `<div class="question-options">
                <div>Escala: 1 (Discordo totalmente) a 6 (Concordo totalmente)</div>
            </div>`;
        }
        
        questionDiv.innerHTML = `
            <input type="checkbox" class="question-checkbox" data-id="${question.id}">
            <span class="question-text"><strong>${question.number}.</strong> ${question.text}</span>
            ${optionsHtml}
        `;
        
        container.appendChild(questionDiv);
    });
}

// Função para renderizar as questões para adicionar ao questionário atual
function renderQuestionsForAdding() {
    const container = document.getElementById('questions-for-adding');
    container.innerHTML = '';
    
    // Obter IDs das questões já selecionadas
    const selectedIds = currentQuestionnaire?.questions.map(q => q.id) || [];
    
    // Renderizar apenas questões que não estão no questionário atual
    allQuestions.forEach(question => {
        if (!selectedIds.includes(question.id)) {
            const questionDiv = document.createElement('div');
            questionDiv.className = 'question-item';
            questionDiv.dataset.id = question.id;
            
            questionDiv.innerHTML = `
                <input type="checkbox" class="question-checkbox" data-id="${question.id}">
                <span class="question-text"><strong>${question.number}.</strong> ${question.text}</span>
            `;
            
            container.appendChild(questionDiv);
            
            // Adicionar evento de clique para adicionar a questão
            const checkbox = questionDiv.querySelector('.question-checkbox');
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    addQuestionToCurrentQuestionnaire(parseInt(this.dataset.id));
                }
            });
        }
    });
}

// Função para renderizar as questões selecionadas no questionário atual
function renderSelectedQuestions() {
    const container = document.getElementById('selected-questions');
    container.innerHTML = '';
    
    if (!currentQuestionnaire || !currentQuestionnaire.questions.length) {
        container.innerHTML = '<p>Nenhuma questão selecionada</p>';
        return;
    }
    
    currentQuestionnaire.questions.forEach((question, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-item';
        
        questionDiv.innerHTML = `
            <div class="question-text">
                <strong>${index + 1}.</strong> ${question.text}
                <button class="btn btn-secondary" style="float: right; padding: 2px 8px;" 
                    onclick="removeQuestionFromCurrentQuestionnaire(${index})">Remover</button>
            </div>
        `;
        
        container.appendChild(questionDiv);
    });
}

// Função para adicionar uma questão ao questionário atual
function addQuestionToCurrentQuestionnaire(questionId) {
    if (!currentQuestionnaire) return;
    
    const question = allQuestions.find(q => q.id === questionId);
    if (question) {
        currentQuestionnaire.questions.push(question);
        renderSelectedQuestions();
        renderQuestionsForAdding(); // Atualiza a lista de questões disponíveis
    }
}

// Função para remover uma questão do questionário atual
function removeQuestionFromCurrentQuestionnaire(index) {
    if (!currentQuestionnaire) return;
    
    currentQuestionnaire.questions.splice(index, 1);
    renderSelectedQuestions();
    renderQuestionsForAdding(); // Atualiza a lista de questões disponíveis
}

// Função para renderizar os questionários salvos
function renderSavedQuestionnaires() {
    const container = document.getElementById('saved-questionnaires');
    container.innerHTML = '';
    
    if (!savedQuestionnaires.length) {
        container.innerHTML = '<p>Nenhum subquestionário salvo</p>';
        return;
    }
    
    savedQuestionnaires.forEach(questionnaire => {
        const questionnaireDiv = document.createElement('div');
        questionnaireDiv.className = 'questionnaire-item';
        
        questionnaireDiv.innerHTML = `
            <div>
                <div class="questionnaire-title">${questionnaire.title}</div>
                <div>${questionnaire.description || 'Sem descrição'}</div>
                <div>${questionnaire.questions.length} questões</div>
            </div>
            <div>
                <button class="btn" onclick="viewQuestionnaire(${questionnaire.id})">Visualizar</button>
            </div>
        `;
        
        container.appendChild(questionnaireDiv);
    });
}

// Função para visualizar um questionário
function viewQuestionnaire(id) {
    const questionnaire = savedQuestionnaires.find(q => q.id === id);
    if (!questionnaire) return;
    
    // Preencher o modal com os dados do questionário
    document.getElementById('view-questionnaire-title').textContent = questionnaire.title;
    document.getElementById('view-questionnaire-description').textContent = questionnaire.description || 'Sem descrição';
    
    const container = document.getElementById('view-questions');
    
    // Adicionar a mensagem introdutória
    const introDiv = document.createElement('div');
    introDiv.className = 'intro-message';
    introDiv.style.backgroundColor = '#f8f9fa';
    introDiv.style.padding = '15px';
    introDiv.style.borderRadius = '5px';
    introDiv.style.marginBottom = '20px';
    
    introDiv.innerHTML = `
        <p><strong>Caro(a) estudante,</strong></p>
        <p>Este questionário constitui um instrumento importante para compor o perfil dos participantes do Enade e o contexto de seus processos formativos. Além disso, é uma oportunidade para você avaliar diversos aspectos do seu curso e da sua formação.</p>
        <p>Sua contribuição é extremamente relevante para acessarmos informações acerca das condições de oferta de seu curso, bem como para subsidiar a avaliação da qualidade da educação superior no país. As respostas às questões serão analisadas em conjunto, por curso de graduação, preservando o sigilo da identidade dos participantes.</p>
        <p>Este instrumento deve ser preenchido exclusivamente por você, não sendo admitidas quaisquer manipulações, influências ou pressões de terceiros. Caso você perceba alguma dessas situações, configurando tentativa de manipulação do preenchimento do questionário, entre em contato com o Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (Inep), por meio dos canais disponíveis para o "Atendimento ao Cidadão", acessível no Portal do Inep.</p>
        <p>Para responder, basta clicar sobre a alternativa desejada. A finalização do preenchimento do questionário será pré-requisito para a visualização do local de prova, que se tornará disponível a partir da data prevista no edital desta edição do Exame, e para fins de obtenção de regularidade perante o Enade 2025.</p>
        <p>Agradecemos a sua colaboração!</p>
    `;
    
    container.innerHTML = '';
    container.appendChild(introDiv);
    
    questionnaire.questions.forEach((question, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-item';
        
        let optionsHtml = '';
        if (question.type === 'multiple-choice') {
            optionsHtml = `<div class="question-options">`;
            question.options.forEach(option => {
                optionsHtml += `<div><strong>${option.label})</strong> ${option.text}</div>`;
            });
            optionsHtml += `</div>`;
        } else if (question.type === 'likert') {
            optionsHtml = `<div class="question-options">
                <div>Escala: 1 (Discordo totalmente) a 6 (Concordo totalmente)</div>
            </div>`;
        }
        
        questionDiv.innerHTML = `
            <div class="question-text"><strong>${index + 1}.</strong> ${question.text}</div>
            ${optionsHtml}
        `;
        
        container.appendChild(questionDiv);
    });
    
    // Configurar o botão de exclusão
    document.getElementById('btn-delete-questionnaire').onclick = function() {
        if (confirm('Tem certeza que deseja excluir este questionário?')) {
            deleteQuestionnaire(id);
            closeViewModal();
        }
    };
    
    // Configurar botões de exportação
    document.getElementById('btn-export-pdf').onclick = function() {
        exportQuestionnaire(id, 'pdf');
    };
    
    document.getElementById('btn-export-html').onclick = function() {
        exportQuestionnaire(id, 'html');
    };
    
    // Exibir o modal
    document.getElementById('view-modal').style.display = 'block';
}

// Função para excluir um questionário
function deleteQuestionnaire(id) {
    savedQuestionnaires = savedQuestionnaires.filter(q => q.id !== id);
    localStorage.setItem('savedQuestionnaires', JSON.stringify(savedQuestionnaires));
    renderSavedQuestionnaires();
}

// Função para exportar questionário
function exportQuestionnaire(id, format) {
    const questionnaire = savedQuestionnaires.find(q => q.id === id);
    if (!questionnaire) return;
    
    if (format === 'pdf') {
        alert('Para exportar como PDF, salve primeiro como HTML e depois use a função de impressão do navegador selecionando "Salvar como PDF".');
        exportQuestionnaire(id, 'html');
        return;
    }
    
    if (format === 'html') {
        let htmlContent = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>${questionnaire.title}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
                h1 { color: #2c3e50; }
                .question { margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
                .question-text { font-weight: bold; }
                .options { margin-left: 20px; margin-top: 5px; }
                .intro-message { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; line-height: 1.6; }
            </style>
        </head>
        <body>
            <h1>${questionnaire.title}</h1>
            <p>${questionnaire.description || ''}</p>
            
            <div class="intro-message">
                <p><strong>Caro(a) estudante,</strong></p>
                <p>Este questionário constitui um instrumento importante para compor o perfil dos participantes do Enade e o contexto de seus processos formativos. Além disso, é uma oportunidade para você avaliar diversos aspectos do seu curso e da sua formação.</p>
                <p>Sua contribuição é extremamente relevante para acessarmos informações acerca das condições de oferta de seu curso, bem como para subsidiar a avaliação da qualidade da educação superior no país. As respostas às questões serão analisadas em conjunto, por curso de graduação, preservando o sigilo da identidade dos participantes.</p>
                <p>Este instrumento deve ser preenchido exclusivamente por você, não sendo admitidas quaisquer manipulações, influências ou pressões de terceiros. Caso você perceba alguma dessas situações, configurando tentativa de manipulação do preenchimento do questionário, entre em contato com o Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (Inep), por meio dos canais disponíveis para o "Atendimento ao Cidadão", acessível no Portal do Inep.</p>
                <p>Para responder, basta clicar sobre a alternativa desejada. A finalização do preenchimento do questionário será pré-requisito para a visualização do local de prova, que se tornará disponível a partir da data prevista no edital desta edição do Exame, e para fins de obtenção de regularidade perante o Enade 2025.</p>
                <p>Agradecemos a sua colaboração!</p>
            </div>
            
            <div id="questions">
        `;
        
        questionnaire.questions.forEach((question, index) => {
            htmlContent += `
                <div class="question">
                    <div class="question-text">${index + 1}. ${question.text}</div>
                    <div class="options">
            `;
            
            if (question.type === 'multiple-choice') {
                question.options.forEach(option => {
                    htmlContent += `<div style="margin: 8px 0;">
                        <input type="radio" name="q${index}" id="q${index}${option.label}" value="${option.label}">
                        <label for="q${index}${option.label}" style="margin-left: 8px; cursor: pointer;">${option.label}) ${option.text}</label>
                    </div>`;
                });
            } else if (question.type === 'likert') {
                htmlContent += `<div style="margin-bottom: 10px;">Escala: 1 (Discordo totalmente) a 6 (Concordo totalmente)</div>
                <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 5px;">`;
                
                for (let i = 1; i <= 6; i++) {
                    htmlContent += `<div style="display: flex; align-items: center; margin-right: 15px;">
                        <input type="radio" name="q${index}" id="q${index}opt${i}" value="${i}">
                        <label for="q${index}opt${i}" style="margin-left: 5px; cursor: pointer;">${i}</label>
                    </div>`;
                }
                
                // Adicionar opções "Não sei responder" e "Não se aplica"
                htmlContent += `
                    <div style="display: flex; align-items: center; margin-right: 15px;">
                        <input type="radio" name="q${index}" id="q${index}optN" value="N">
                        <label for="q${index}optN" style="margin-left: 5px; cursor: pointer;">Não sei responder</label>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <input type="radio" name="q${index}" id="q${index}optNA" value="NA">
                        <label for="q${index}optNA" style="margin-left: 5px; cursor: pointer;">Não se aplica</label>
                    </div>
                </div>`;
            }
            
            htmlContent += `
                    </div>
                </div>
            `;
        });
        
        // Adicionar campos de identificação do aluno
        htmlContent += `
            </div>
            
            <div id="student-info" style="margin-top: 30px; margin-bottom: 20px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9;">
                <h3>Informações do Aluno</h3>
                <div style="margin-bottom: 15px;">
                    <label for="student-name" style="display: block; margin-bottom: 5px; font-weight: bold;">Nome Completo:</label>
                    <input type="text" id="student-name" name="student-name" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
                <div style="margin-bottom: 15px;">
                    <label for="student-id" style="display: block; margin-bottom: 5px; font-weight: bold;">Matrícula:</label>
                    <input type="text" id="student-id" name="student-id" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
                <div style="margin-bottom: 15px;">
                    <label for="student-email" style="display: block; margin-bottom: 5px; font-weight: bold;">E-mail:</label>
                    <input type="email" id="student-email" name="student-email" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                </div>
            </div>
            
            <button id="submit-btn" style="display: block; margin: 20px auto; padding: 10px 20px; background-color: #3498db; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer;">Enviar Respostas</button>
            
            <div id="result-message" style="display: none; margin-top: 20px; padding: 15px; border-radius: 5px;"></div>
            
            <script>
                // Validar o formulário antes de enviar
                document.getElementById('submit-btn').addEventListener('click', function() {
                    const studentName = document.getElementById('student-name').value.trim();
                    const studentId = document.getElementById('student-id').value.trim();
                    const studentEmail = document.getElementById('student-email').value.trim();
                    
                    // Verificar se os campos obrigatórios foram preenchidos
                    if (!studentName || !studentId) {
                        alert('Por favor, preencha o nome e a matrícula.');
                        return;
                    }
                    
                    // Verificar se todas as questões foram respondidas
                    const questions = document.querySelectorAll('.question');
                    let unansweredQuestions = [];
                    
                    questions.forEach((question, index) => {
                        const questionInputs = question.querySelectorAll('input[type="radio"]');
                        let answered = false;
                        
                        questionInputs.forEach(input => {
                            if (input.checked) {
                                answered = true;
                            }
                        });
                        
                        if (!answered) {
                            unansweredQuestions.push(index + 1);
                        }
                    });
                    
                    if (unansweredQuestions.length > 0) {
                        alert('Por favor, responda a todas as questões. Questões não respondidas: ' + unansweredQuestions.join(', '));
                        return;
                    }
                    
                    // Coletar as respostas
                    const responses = [];
                    questions.forEach((question, index) => {
                        const questionText = question.querySelector('.question-text').textContent;
                        let selectedOption = '';
                        
                        const options = question.querySelectorAll('input[type="radio"]');
                        options.forEach(option => {
                            if (option.checked) {
                                const label = option.nextElementSibling.textContent;
                                selectedOption = label;
                            }
                        });
                        
                        responses.push({
                            question: questionText,
                            answer: selectedOption
                        });
                    });
                    
                    // Criar o objeto de resposta
                    const submission = {
                        studentName: studentName,
                        studentId: studentId,
                        studentEmail: studentEmail,
                        questionnaire: "${questionnaire.title}",
                        submissionDate: new Date().toISOString(),
                        responses: responses
                    };
                    
                    // Exibir mensagem de sucesso
                    const resultMessage = document.getElementById('result-message');
                    resultMessage.style.display = 'block';
                    resultMessage.style.backgroundColor = '#d4edda';
                    resultMessage.style.borderColor = '#c3e6cb';
                    resultMessage.style.color = '#155724';
                    resultMessage.innerHTML = '<strong>Respostas enviadas com sucesso!</strong><br>Obrigado por completar o questionário.';
                    
                    // Desabilitar o botão de envio para evitar múltiplos envios
                    document.getElementById('submit-btn').disabled = true;
                    
                    // Em um sistema real, você enviaria os dados para um servidor
                    // Enviar ao servidor FastAPI
                    fetch("http://localhost:8000/api/responses", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(submission)
                    })
                    .then(res => res.json())
                    .then(data => {
                        resultMessage.innerHTML += "<br><em>" + data.message + "</em>";
                    })
                    .catch(error => {
                        console.error("Erro ao enviar resposta:", error);
                        resultMessage.innerHTML += "<br><span style='color: red;'>Erro ao enviar para o servidor.</span>";
                    });
                    
                    // Opção para salvar localmente (útil para testes)
                    //localStorage.setItem('questionnaireResponse_' + Date.now(), JSON.stringify(submission));
                    
                    // Opcional: Adicionar um botão para baixar as respostas como JSON
                    const downloadBtn = document.createElement('button');
                    downloadBtn.textContent = 'Baixar Respostas (JSON)';
                    downloadBtn.style.display = 'block';
                    downloadBtn.style.margin = '10px auto';
                    downloadBtn.style.padding = '8px 15px';
                    downloadBtn.style.backgroundColor = '#17a2b8';
                    downloadBtn.style.color = 'white';
                    downloadBtn.style.border = 'none';
                    downloadBtn.style.borderRadius = '4px';
                    downloadBtn.style.cursor = 'pointer';
                    
                    downloadBtn.addEventListener('click', function() {
                        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(submission, null, 2));
                        const downloadAnchorNode = document.createElement('a');
                        downloadAnchorNode.setAttribute("href", dataStr);
                        downloadAnchorNode.setAttribute("download", "respostas_" + studentId + ".json");
                        document.body.appendChild(downloadAnchorNode);
                        downloadAnchorNode.click();
                        downloadAnchorNode.remove();
                    });
                    
                    //resultMessage.appendChild(downloadBtn);
                });
            </script>
        </body>
        </html>
        `;
        
        // Criar um link para download do arquivo HTML
        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/html;charset=utf-8,' + encodeURIComponent(htmlContent));
        element.setAttribute('download', `${questionnaire.title.replace(/\s+/g, '_')}.html`);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    }
}

// Funções para manipular respostas dos alunos
function loadResponses() {
    const questionnairesFilter = document.getElementById('filter-questionnaire').value;
    const studentSearch = document.getElementById('search-student').value.toLowerCase();
    
    const responsesContainer = document.getElementById('responses-container');
    responsesContainer.innerHTML = '';

    const template = document.getElementById('response-template');

    fetch("/api/responses")
        .then(res => res.json())
        .then(responses => {
            // Filtro por questionário
            if (questionnairesFilter) {
                responses = responses.filter(r => r.questionnaire === questionnairesFilter);
            }

            // Filtro por nome/matrícula
            if (studentSearch) {
                responses = responses.filter(r => 
                    (r.studentName && r.studentName.toLowerCase().includes(studentSearch)) ||
                    (r.studentId && r.studentId.toLowerCase().includes(studentSearch))
                );
            }

            if (responses.length === 0) {
                document.getElementById('no-responses').style.display = 'block';
                return;
            } else {
                document.getElementById('no-responses').style.display = 'none';
            }

            responses.forEach((response, index) => {
                const clone = document.importNode(template.content, true);
                
                clone.querySelector('.student-name').textContent = response.studentName;
                clone.querySelector('.student-id').textContent = response.studentId;
                clone.querySelector('.questionnaire-name').textContent = response.questionnaire;
                clone.querySelector('.submission-date').textContent = new Date(response.submissionDate).toLocaleString();
                
                const viewButton = clone.querySelector('.btn');
                viewButton.setAttribute('data-index', index);
                viewButton.onclick = () => showResponseDetails(response);

                responsesContainer.appendChild(clone);
            });
        })
        .catch(err => {
            console.error("Erro ao carregar respostas do servidor:", err);
            document.getElementById('no-responses').style.display = 'block';
        });
}

function showResponseDetails(responseData) {
    document.getElementById('response-student-name').textContent = responseData.studentName;
    document.getElementById('response-student-id').textContent = responseData.studentId;
    document.getElementById('response-student-email').textContent = responseData.studentEmail || 'Não informado';
    document.getElementById('response-questionnaire-name').textContent = responseData.questionnaire;
    document.getElementById('response-submission-date').textContent = new Date(responseData.submissionDate).toLocaleString();

    const answersContainer = document.getElementById('response-answers');
    answersContainer.innerHTML = '';

    responseData.responses.forEach((resposta, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-item';
        questionDiv.innerHTML = `
            <div class="question-text"><strong>Questão ${index + 1}:</strong> ${resposta.question}</div>
            <div class="question-answer" style="margin-left: 20px;"><strong>Resposta:</strong> ${resposta.answer}</div>
        `;
        answersContainer.appendChild(questionDiv);
    });

    document.getElementById('btn-export-response').onclick = function () {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(responseData, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", `resposta_${responseData.studentId}_${responseData.questionnaire.replace(/\s+/g, '_')}.json`);
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    };

    document.getElementById('btn-delete-response').style.display = 'none'; // Desabilita se não for mais usar

    document.getElementById('response-modal').style.display = 'block';
}

function viewResponse(responseId) {
    // Obter a resposta do localStorage
    const responseData = JSON.parse(localStorage.getItem(responseId));
    if (!responseData) return;
    
    // Preencher o modal com os dados da resposta
    document.getElementById('response-student-name').textContent = responseData.studentName;
    document.getElementById('response-student-id').textContent = responseData.studentId;
    document.getElementById('response-student-email').textContent = responseData.studentEmail || 'Não informado';
    document.getElementById('response-questionnaire-name').textContent = responseData.questionnaire;
    document.getElementById('response-submission-date').textContent = new Date(responseData.submissionDate).toLocaleString();
    
    // Preencher as respostas
    const answersContainer = document.getElementById('response-answers');
    answersContainer.innerHTML = '';
    
    responseData.responses.forEach((response, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-item';
        
        questionDiv.innerHTML = `
            <div class="question-text"><strong>Questão ${index + 1}:</strong> ${response.question}</div>
            <div class="question-answer" style="margin-left: 20px;"><strong>Resposta:</strong> ${response.answer}</div>
        `;
        
        answersContainer.appendChild(questionDiv);
    });
    
    // Configurar botões de exportação e exclusão
    document.getElementById('btn-export-response').onclick = function() {
        exportResponse(responseId);
    };
    
    document.getElementById('btn-delete-response').onclick = function() {
        if (confirm('Tem certeza que deseja excluir esta resposta?')) {
            localStorage.removeItem(responseId);
            closeResponseModal();
            loadResponses(); // Recarregar a lista de respostas
        }
    };
    
    // Exibir o modal
    document.getElementById('response-modal').style.display = 'block';
}

function exportResponse(responseId) {
    const responseData = JSON.parse(localStorage.getItem(responseId));
    if (!responseData) return;
    
    // Criar um objeto para download
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(responseData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `resposta_${responseData.studentId}_${responseData.questionnaire.replace(/\s+/g, '_')}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}

function closeResponseModal() {
    document.getElementById('response-modal').style.display = 'none';
}

function populateQuestionnaireFilter() {
    const select = document.getElementById('filter-questionnaire');
    select.innerHTML = '<option value="">Todos os Subquestionários</option>';
    
    // Adicionar opções para cada questionário salvo
    savedQuestionnaires.forEach(questionnaire => {
        const option = document.createElement('option');
        option.value = questionnaire.title;
        option.textContent = questionnaire.title;
        select.appendChild(option);
    });
}

// Filtrar questões
function filterQuestions() {
    const searchText = document.getElementById('search-questions').value.toLowerCase();
    const categoryFilter = document.getElementById('filter-category').value;
    const typeFilter = document.getElementById('filter-type').value;
    
    const questions = document.querySelectorAll('#all-questions-container .question-item');
    
    questions.forEach(question => {
        const text = question.querySelector('.question-text').textContent.toLowerCase();
        const category = question.dataset.category;
        const type = question.dataset.type;
        
        const matchesSearch = searchText === '' || text.includes(searchText);
        const matchesCategory = categoryFilter === '' || category === categoryFilter;
        const matchesType = typeFilter === '' || type === typeFilter;
        
        if (matchesSearch && matchesCategory && matchesType) {
            question.style.display = '';
        } else {
            question.style.display = 'none';
        }
    });
}

// Filtrar questões para adicionar
function filterQuestionsForAdding() {
    const searchText = document.getElementById('search-for-adding').value.toLowerCase();
    
    const questions = document.querySelectorAll('#questions-for-adding .question-item');
    
    questions.forEach(question => {
        const text = question.querySelector('.question-text').textContent.toLowerCase();
        
        if (text.includes(searchText)) {
            question.style.display = '';
        } else {
            question.style.display = 'none';
        }
    });
}

// Fechar modal de criação
function closeCreateModal() {
    document.getElementById('create-modal').style.display = 'none';
}

// Fechar modal de visualização
function closeViewModal() {
    document.getElementById('view-modal').style.display = 'none';
}

// Iniciar a criação de um questionário
function startQuestionnaireCreation(title, description) {
    currentQuestionnaire = {
        title: title,
        description: description,
        questions: []
    };
    
    document.getElementById('current-questionnaire-title').textContent = title;
    document.getElementById('current-questionnaire-description').textContent = description || 'Sem descrição';
    document.getElementById('current-questionnaire-info').style.display = 'block';
    
    renderQuestionsForAdding();
    renderSelectedQuestions();
}

// Cancelar a criação de um questionário
function cancelQuestionnaireCreation() {
    currentQuestionnaire = null;
    document.getElementById('current-questionnaire-info').style.display = 'none';
}

// Salvar um questionário
function saveQuestionnaire() {
    if (!currentQuestionnaire) return;
    
    // Verificar se já existem questionários salvos
    if (!savedQuestionnaires.length) {
        currentQuestionnaire.id = 1;
    } else {
        // Encontrar o maior ID e incrementar 1
        const maxId = Math.max(...savedQuestionnaires.map(q => q.id));
        currentQuestionnaire.id = maxId + 1;
    }
    
    // Adicionar timestamp de criação
    currentQuestionnaire.createdAt = new Date().toISOString();
    
    // Salvar o questionário
    savedQuestionnaires.push(currentQuestionnaire);
    localStorage.setItem('savedQuestionnaires', JSON.stringify(savedQuestionnaires));
    
    // Resetar o questionário atual
    cancelQuestionnaireCreation();
    
    // Mostrar mensagem de sucesso
    alert('Subquestionário salvo com sucesso!');
    
    // Mudar para a aba de questionários salvos
    document.querySelector('.tab[data-tab="tab-saved"]').click();
}

// Função para selecionar todas as questões para licenciaturas
function selectQuestionsLicenciaturas() {
    if (!currentQuestionnaire) return;
    
    // Limpar questões atualmente selecionadas
    currentQuestionnaire.questions = [];
    
    // Adicionar todas as questões ao questionário atual
    allQuestions.forEach(question => {
        // Adicionar apenas se não estiver já incluída
        const found = currentQuestionnaire.questions.some(q => q.id === question.id);
        if (!found) {
            currentQuestionnaire.questions.push(question);
        }
    });
    
    // Atualizar a visualização
    renderSelectedQuestions();
    renderQuestionsForAdding();
}

// Função para selecionar questões 1-44 para outros cursos
function selectQuestionsOutrosCursos() {
    if (!currentQuestionnaire) return;
    
    // Limpar questões atualmente selecionadas
    currentQuestionnaire.questions = [];
    
    // Adicionar questões de 1 a 44 ao questionário atual
    allQuestions.forEach(question => {
        if (question.number >= 1 && question.number <= 44) {
            // Adicionar apenas se não estiver já incluída
            const found = currentQuestionnaire.questions.some(q => q.id === question.id);
            if (!found) {
                currentQuestionnaire.questions.push(question);
            }
        }
    });
    
    // Atualizar a visualização
    renderSelectedQuestions();
    renderQuestionsForAdding();
}

// Configurar event listeners quando a página carrega
document.addEventListener('DOMContentLoaded', function() {
    // Configurar os event listeners para as abas
    document.querySelectorAll('.tabs .tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            openTab(this, tabId);
        });
    });
    
    // Modal de criar questionário
    const createModal = document.getElementById('create-modal');
    const btnOpenCreateModal = document.getElementById('btn-open-create-modal');
    const createCloseBtn = createModal.querySelector('.close');
    
    btnOpenCreateModal.onclick = function() {
        createModal.style.display = 'block';
    };
    
    createCloseBtn.onclick = function() {
        closeCreateModal();
    };
    
    // Modal de visualizar questionário
    const viewModal = document.getElementById('view-modal');
    const viewCloseBtn = viewModal.querySelector('.close');
    
    viewCloseBtn.onclick = function() {
        closeViewModal();
    };
    
    // Modal de visualizar resposta
    const responseModal = document.getElementById('response-modal');
    const responseCloseBtn = responseModal.querySelector('.close');
    
    responseCloseBtn.onclick = function() {
        closeResponseModal();
    };
    
    // Quando clicar fora do modal, fechar
    window.onclick = function(event) {
        if (event.target === createModal) {
            closeCreateModal();
        } else if (event.target === viewModal) {
            closeViewModal();
        } else if (event.target === responseModal) {
            closeResponseModal();
        }
    };
    
    // Formulário de criação de questionário
    document.getElementById('form-questionnaire').onsubmit = function(e) {
        e.preventDefault();
        
        const title = document.getElementById('questionnaire-title').value;
        const description = document.getElementById('questionnaire-description').value;
        
        closeCreateModal();
        startQuestionnaireCreation(title, description);
    };
    
    // Botão de salvar questionário
    document.getElementById('btn-save-questionnaire').onclick = function() {
        if (currentQuestionnaire.questions.length === 0) {
            alert('Adicione pelo menos uma questão ao questionário!');
            return;
        }
        
        saveQuestionnaire();
    };
    
    // Botão de cancelar criação
    document.getElementById('btn-cancel-creation').onclick = function() {
        if (confirm('Tem certeza que deseja cancelar a criação do questionário?')) {
            cancelQuestionnaireCreation();
        }
    };
    
    // Renderizar questionários salvos
    renderSavedQuestionnaires();
});

// Funções globais para serem acessadas pelo inline onclick
window.viewQuestionnaire = viewQuestionnaire;
window.removeQuestionFromCurrentQuestionnaire = removeQuestionFromCurrentQuestionnaire;
window.viewResponse = viewResponse;
window.loadResponses = loadResponses;
window.selectQuestionsLicenciaturas = selectQuestionsLicenciaturas;
window.selectQuestionsOutrosCursos = selectQuestionsOutrosCursos;