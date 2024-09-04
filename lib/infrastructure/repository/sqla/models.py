from datetime import datetime
from typing import Dict, List, Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    Index,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Table,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import mapped_column, object_mapper, relationship, Mapped, MappedColumn
from sqlalchemy.orm.session import Session

from lib.infrastructure.repository.sqla.database import Base
from lib.core.entity.models import ProtocolEnum, SourceDataStatusEnum


class ModelBase(object):
    """
    Base class for Kernel Planckster Models
    """

    __table_initialized__ = False

    @declared_attr  # type: ignore
    def __table_args__(cls: Base) -> tuple:  # type: ignore # pylint: disable=no-self-argument
        # pylint: disable=maybe-no-member
        return (
            CheckConstraint("CREATED_AT IS NOT NULL", name=cls.__tablename__.upper() + "_CREATED_NN"),
            CheckConstraint("UPDATED_AT IS NOT NULL", name=cls.__tablename__.upper() + "_UPDATED_NN"),
            {"mysql_engine": "InnoDB"},
        )

    @declared_attr
    def created_at(cls) -> MappedColumn[Any]:  # pylint: disable=no-self-argument
        return mapped_column("created_at", DateTime, default=datetime.utcnow)

    @declared_attr
    def updated_at(cls) -> MappedColumn[Any]:  # pylint: disable=no-self-argument
        return mapped_column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self, flush: bool = True, session: Session | None = None) -> None:
        """Save this object"""
        # Sessions created with autoflush=True be default since sqlAlchemy 1.4.
        # So explicatly calling session.flush is not necessary.
        # However, when autogenerated primary keys involved, calling
        # session.flush to get the id from DB.
        if not session:
            raise Exception("Session not found")

        session.add(self)
        if flush:
            session.flush()

    def delete(self, flush: bool = True, session: Session | None = None) -> None:
        """Delete this object"""
        if not session:
            raise Exception("Session not found")

        session.delete(self)
        if flush:
            session.flush()

    def update(self, values: dict[Any, Any], flush: bool = True, session: Session | None = None) -> None:
        """dict.update() behaviour."""
        if not session:
            raise Exception("Session not found")

        for k, v in values.items():
            self[k] = v
        if session and flush:
            session.flush()

    def __setitem__(self, key: Any, value: Any) -> None:
        setattr(self, key, value)

    def __getitem__(self, key: Any) -> Any:
        return getattr(self, key)

    def __iter__(self) -> "ModelBase":
        self._i = iter(object_mapper(self).columns)
        return self

    def __next__(self) -> tuple[str, Any]:
        n = next(self._i).name
        return n, getattr(self, n)

    def keys(self) -> list[str]:
        return list(self.__dict__.keys())

    def values(self) -> list[Any]:
        return list(self.__dict__.values())

    def items(self) -> list[tuple[str, Any]]:
        return list(self.__dict__.items())

    def to_dict(self) -> Dict[str, Any]:
        dictionary = self.__dict__.copy()
        dictionary.pop("_sa_instance_state")
        return dictionary

    next = __next__


class SoftModelBase(ModelBase):
    """
    Base class for Kernel Planckster Models with soft-deletion support
    """

    __table_initialized__ = False

    @declared_attr  # type: ignore
    def __table_args__(cls: Base) -> tuple:  # type: ignore
        # pylint: disable=no-self-argument
        # pylint: disable=maybe-no-member
        return (
            CheckConstraint("CREATED_AT IS NOT NULL", name=cls.__tablename__.upper() + "_CREATED_NN"),
            CheckConstraint("UPDATED_AT IS NOT NULL", name=cls.__tablename__.upper() + "_UPDATED_NN"),
            CheckConstraint("DELETED IS NOT NULL", name=cls.__tablename__.upper() + "_DELETED_NN"),
            {"mysql_engine": "InnoDB"},
        )

    @declared_attr
    def deleted(cls: Base) -> MappedColumn[Any]:  # pylint: disable=no-self-argument
        return mapped_column("deleted", Boolean, default=False)

    @declared_attr
    def deleted_at(cls: Base) -> MappedColumn[Any]:  # pylint: disable=no-self-argument
        return mapped_column("deleted_at", DateTime, nullable=True)

    def delete(self, flush: bool = True, session: Session | None = None) -> None:
        """Delete this object"""
        self.deleted = True  # TODO: typing: if session is None, it doesn't have delete
        self.deleted_at = datetime.utcnow()  # TODO: typing: if session is None, it doesn't have deleted_at
        self.save(session=session)  # TODO: typing: if session is None, it doesn't have save


class SQLAClient(Base, SoftModelBase):  # type: ignore
    """
    SQLAlchemy Client model

    @param id: The ID of the client
    @type id: int
    param sub: The SUB of the client
    @type sub: str
    @param research_contexts: The research contexts of the client
    @type research_contexts: List[SQLAResearchContext]
    """

    __tablename__ = "client"

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    sub: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    research_contexts: Mapped[List["SQLAResearchContext"]] = relationship("SQLAResearchContext", backref="client")

    source_data: Mapped[List["SQLASourceData"]] = relationship(
        "SQLASourceData", backref="client", cascade="all, delete"
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id})>"


SourceDataResearchContextAssociation = Table(
    "source_data_research_context_association",
    Base.metadata,
    Column("source_data_id", Integer, ForeignKey("source_data.id")),
    Column("research_context_id", Integer, ForeignKey("research_context.id")),
)


class SQLASourceData(Base, SoftModelBase):  # type: ignore
    """
    SQLAlchemy Source Data model

    @param id: The ID of the source data
    @type id: int
    @param name: The name of the source data
    @type name: str
    @param relative_path: The relative path of the source data
    @type relative_path: str
    @param type: The type of the source data
    @type type: str
    @param protocol: The protocol of the source data
    @type protocol: ProtocolEnum
    @param status: The status of the source data
    @type status: SourceDataStatusEnum
    @param client_id: The ID of the client of the source data
    @type client_id: int
    @param citations: The citations of the source data by the llm associated to the research contexts this source data belongs to
    @type citations: List[SQLACitation]

    :composite_index: client_id, relative_path, protocol
    """

    __tablename__ = "source_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    relative_path: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    protocol: Mapped[ProtocolEnum] = mapped_column(SAEnum(ProtocolEnum), nullable=False)
    status: Mapped[SourceDataStatusEnum] = mapped_column(SAEnum(SourceDataStatusEnum), nullable=False)

    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), nullable=False)
    citations: Mapped[List["SQLACitation"]] = relationship("SQLACitation", backref="source_data")

    __table_args__ = (Index("uix_client_id_relative_path_protocol", "client_id", "relative_path", "protocol", unique=True),)  # type: ignore

    def __repr__(self) -> str:
        return f"<SourceData (id={self.id}, name={self.name})>"


EmbeddingModelLLMAssociation = Table(
    "embedding_model_llm_association",
    Base.metadata,
    Column("embedding_model_id", Integer, ForeignKey("embedding_model.id")),
    Column("llm_id", Integer, ForeignKey("llm.id")),
)


class SQLAEmbeddingModel(Base, SoftModelBase):  # type: ignore
    """
    SQLAlchemy Embedding Model model

    @param id: The ID of the embedding model
    @type id: int
    @param name: The name of the embedding model
    @type name: str
    @param vector_stores: The vector stores of the embedding model
    @type vector_stores: List[SQLAVectorStore]
    """

    __tablename__ = "embedding_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    vector_stores: Mapped[List["SQLAVectorStore"]] = relationship("SQLAVectorStore", backref="embedding_model")


class SQLALLM(Base, SoftModelBase):  # type: ignore
    """
    SQLAlchemy LLM model

    @param id: The ID of the llm
    @type id: int
    @param llm_name: The name of the llm
    @type llm_name: str
    @param embedding_models: The embedding models of the llm
    @type embedding_models: List[SQLAEmbeddingModel]
    @param research_contexts: The research contexts of the llm
    @type research_contexts: List[SQLAResearchContext]
    """

    __tablename__ = "llm"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    llm_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    embedding_models: Mapped[List["SQLAEmbeddingModel"]] = relationship(
        "SQLAEmbeddingModel", secondary=EmbeddingModelLLMAssociation
    )
    research_contexts: Mapped[List["SQLAResearchContext"]] = relationship("SQLAResearchContext", backref="llm")


class SQLAVectorStore(Base, ModelBase):  # type: ignore
    """
    SQLAlchemy Vector Store model

    @param id: The ID of the vector store
    @type id: int
    @param name: The name of the vector store
    @type name: str
    @param lfn: The LFN of the vector store. Must be a valid serialized LFN
    @type lfn: str
    @param research_context_id: The ID of the research context of the vector store
    @type research_context_id: int
    @param research_context: The research context of the vector store
    @type research_context: SQLAResearchContext
    @param embedding_model_id: The ID of the embedding model of the vector store
    @type embedding_model_id: int
    """

    __tablename__ = "vector_store"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    lfn: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    research_context_id: Mapped[int] = mapped_column(ForeignKey("research_context.id"), nullable=True)
    research_context: Mapped["SQLAResearchContext"] = relationship("SQLAResearchContext", back_populates="vector_store")
    embedding_model_id: Mapped[int] = mapped_column(ForeignKey("embedding_model.id"), nullable=False)


class SQLAResearchContext(Base, SoftModelBase):  # type: ignore
    """
    SQLAlchemy Research Context model

    @param id: The ID of the research context
    @type id: int
    @param title: The title of the research context
    @type title: str
    @param description: The description of the research context
    @type description: str
    @param client_id: The ID of the client of the research context
    @type client_id: str
    @param llm_id: The ID of the llm of the research context
    @type llm_id: int
    @param source_data: The source data of the research context
    @type source_data: List[SQLASourceData]
    @param vector_store: The vector store of the research context
    @type vector_store: SQLAVectorStore
    @param conversations: The conversations of the research context
    @type conversations: List[SQLAConversation]
    """

    __tablename__ = "research_context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), nullable=False)
    llm_id: Mapped[int] = mapped_column(ForeignKey("llm.id"), nullable=False)
    source_data: Mapped[List["SQLASourceData"]] = relationship(
        "SQLASourceData", secondary=SourceDataResearchContextAssociation
    )
    vector_store: Mapped["SQLAVectorStore"] = relationship(
        "SQLAVectorStore", back_populates="research_context", uselist=False
    )
    conversations: Mapped[List["SQLAConversation"]] = relationship("SQLAConversation", backref="research_context")


class SQLAConversation(Base, SoftModelBase):  # type: ignore
    """
    SQLAlchemy Conversation model

    @param id: The ID of the conversation
    @type id: int
    @param title: The title of the conversation
    @type title: str
    @param research_context_id: The ID of the research context of the conversation
    @type research_context_id: int
    @param message_segments: The message segments of the conversation
    @type message_segments: List[SQLAMessageBase]
    """

    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    research_context_id = mapped_column(ForeignKey("research_context.id"), nullable=False)
    messages: Mapped[List["SQLAMessageBase"]] = relationship("SQLAMessageBase", backref="conversation")


class SQLACitation(Base, SoftModelBase):  # type: ignore
    """
    SQLAlchemy Citation model

    @param id: The ID of the citation
    @type id: int
    @param source_data_id: The ID of the source data of the citation
    @type source_data_id: int
    @param citation_metadata: The metadata of the citation
    @type citation_metadata: str
    @param agent_message_id: The ID of the message response of the citation
    @type agent_message_id: int
    """

    __tablename__ = "citation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_data_id: Mapped[int] = mapped_column(ForeignKey("source_data.id"), nullable=False)
    citation_metadata: Mapped[str] = mapped_column(String, nullable=False)
    agent_message_id: Mapped[int] = mapped_column(ForeignKey("agent_message.id"), nullable=False)


class SQLAMessageBase(Base, SoftModelBase):  # type: ignore
    """
    SQLAlchemy Message Base model

    @param id: The ID of the message
    @type id: int
    @param thread_id: The ID of the thread of the message
    @type thread_id: int
    @param timestamp: The timestamp of the message
    @type timestamp: datetime
    @param type: The type of the message
    @type type: str
    @param message_contents: A list of the content pieces of the message
    @type message_contents: List[SQLAMessageContent]
    @param conversation_id: The ID of the conversation containing the message
    @type conversation_id: int
    """

    __tablename__ = "message_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    type: Mapped[str]

    message_contents: Mapped[List["SQLAMessageContent"]] = relationship(
        "SQLAMessageContent", backref="message_base"
    )
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversation.id"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "message_base",
        "polymorphic_on": "type",
    }


class SQLAUserMessage(SQLAMessageBase):
    """
    SQLAlchemy Message Query model

    @param id: The ID of the message
    @type id: int
    @param thread_id: The ID of the thread of the message
    @type thread_id: int
    @param message_timestamp: The timestamp of the message
    @type message_timestamp: datetime
    @param type: The type of the message
    @type type: str
    @param message_contents: The content pieces of the message
    @type message_contents: List[SQLAMessageContent]
    @param conversation_id: The ID of the conversation containing the message
    @type conversation_id: int
    """

    __tablename__ = "user_message"

    id: Mapped[int] = mapped_column(ForeignKey("message_base.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": "user_message",
    }


class SQLAAgentMessage(SQLAMessageBase):
    """
    SQLAlchemy Message Response model

    @param id: The ID of the message
    @type id: int
    @param thread_id: The ID of the thread of the message
    @type thread_id: int
    @param type: The type of the message
    @type type: str
    @param message_contents: The content pieces of the message
    @type message_contents: List[SQLAMessageContent]
    @param conversation_id: The ID of the conversation containing the message
    @type conversation_id: int
    @param citations: The citations from source data used to produce the message
    @type citations: List[SQLACitation]
    @param source_data: The source data used to produce the message
    @type source_data: List[SQLASourceData]
    """

    __tablename__ = "agent_message"

    id: Mapped[int] = mapped_column(ForeignKey("message_base.id"), primary_key=True)
    citations: Mapped[List["SQLACitation"]] = relationship(
        "SQLACitation", backref="agent_message"
    )
    source_data: Mapped[List["SQLASourceData"]] = relationship(
        "SQLASourceData", secondary=SQLACitation.__tablename__, backref="agent_message"
    )

    __mapper_args__ = {
        "polymorphic_identity": "agent_message",
    }

class SQLAMessageContent(Base, SoftModelBase): # type: ignore
    """
    SQLAlchemy Message Content model

    @param id: The ID of the message content
    @type id: int
    @param content: The piece of content of the message
    @type content: str
    @param message_id: The ID of the message containing the message content
    @type message_segments: int
    """

    __tablename__ = "message_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String, nullable=False)

    message_id: Mapped[int] = mapped_column(ForeignKey("message_base.id"), nullable=False)
