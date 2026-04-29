# =============================================================================
# INFRASTRUCTURE: infrastructure/engines/base_engine.py
# =============================================================================
# Classe abstrata (ABC) que define o contrato comum para todos os engines OCR.
#
# Por que existe:
#   Problema P5 do PRD — cada engine tinha interface diferente, tornando
#   impossível tratá-los de forma uniforme. Com BaseOCREngine, o chamador
#   (application/process_document.py) opera sobre qualquer engine sem saber
#   qual é o concreto — basta chamar engine.process(content, metadata).
#
# Pattern: Strategy + Template Method
#   BaseOCREngine é o "contexto" que define WHAT (a interface pública).
#   Cada subclasse é o "strategy" que define HOW (a implementação concreta).
#
# Para adicionar um novo engine:
#   1. Criar um arquivo em infrastructure/engines/
#   2. Herdar de BaseOCREngine
#   3. Implementar as propriedades/métodos marcados como @abstractmethod
#   4. Registrar o nome no domain/engine_resolver.py (ENGINE_DEFAULTS / CAPABILITIES)
#
# Contrato mínimo obrigatório:
#   - name: str — identificador único do engine ("tesseract", "paddle", ...)
#   - process(content, metadata) → dict — executa OCR e retorna resultado estruturado
#
# Estrutura garantida do dict retornado por process():
#   raw_text:          str   — texto extraído pelo OCR
#   raw_text_fallback: str   — texto ou mensagem para uso como fallback
#   document_info:     dict  — metadados do documento (ex: page_count)
#   entities:          dict  — entidades detectadas (datas, CNPJs, etc.)
#   tables:            list  — tabelas detectadas
#   totals:            dict  — totais monetários detectados
#   _meta:             dict  — metadados do engine (nome, confiança, tempo, etc.)
# =============================================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseOCREngine(ABC):
    """
    Contrato abstrato para todos os engines OCR do projeto.

    Uso esperado em application/process_document.py (Fase 5):

        engine = engine_registry.get(engine_name)   # retorna instância concreta
        result = engine.process(content, metadata)  # mesmo call para qualquer engine

    Para adicionar um novo engine: herdar desta classe e implementar name + process.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Identificador único do engine.
        Ex: "tesseract", "paddle", "openrouter", "docling".
        Deve corresponder aos valores em domain/engine_resolver.py (ENGINE_DEFAULTS).
        """
        ...

    @abstractmethod
    def process(self, content: Any, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Executa OCR no conteúdo fornecido e retorna resultado estruturado.

        Args:
            content:  Bytes do arquivo (imagem ou PDF), caminho de arquivo,
                      ou dict com as chaves 'original' e/ou 'preprocessed'.
            metadata: Metadados opcionais do documento. Chaves relevantes:
                        - doc_type: str  — classificação do documento
                          ('digital_pdf' | 'scanned_image' | 'handwritten_complex')
                        - filename: str  — nome original do arquivo
                        - timeout_s: int — timeout HTTP (engines com APIs externas)

        Returns:
            dict garantido com as seguintes chaves:
              raw_text:          str
              raw_text_fallback: str
              document_info:     dict
              entities:          dict
              tables:            list
              totals:            dict
              _meta:             dict  (sempre inclui 'engine': str)
        """
        ...
