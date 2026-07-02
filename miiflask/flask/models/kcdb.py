#! /usr/bin/env python3
# vim:fenc=utf-8
#
# Copyright © 2026 Ryan Mackenzie White <ryan.white4@canada.ca>
#
# Distributed under terms of the Copyright © Her Majesty the Queen in Right of Canada, as represented by the Minister of Statistics Canada, 2019. license.

"""

"""
from miiflask.flask.db import Base
from miiflask.flask.models.model import kcdb_classifier_map
from miiflask.flask.models.model import kcdb_measurand_map

from sqlalchemy import (ForeignKey,
                        Column,
                        Integer,
                        String,
                        Table,
                        Text,
                        UnicodeText,
                        Boolean,
                        Float,
                        )
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional

# MRA SIM Calibration and Measurement Capabilities entries in the KCDB
class KcdbCmc(Base):
    __tablename__ = "kcdbcmc"
    id: Mapped[int] = mapped_column(primary_key=True)
    kcdbCode: Mapped[str] = mapped_column(String(50))
    baseUnit: Mapped[str] = mapped_column(UnicodeText)
    uncertaintyBaseUnit: Mapped[str] = mapped_column(UnicodeText)
    internationalStandard: Mapped[Optional[str]] = mapped_column(UnicodeText)
    comments: Mapped[str] = mapped_column(UnicodeText)

    area_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbarea.id"))
    area: Mapped['KcdbArea'] = relationship()

    branch_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbbranch.id"))
    branch: Mapped['KcdbBranch'] = relationship()

    service_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbservice.id"))
    service: Mapped['KcdbService'] = relationship()

    subservice_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbsubservice.id"))
    subservice: Mapped['KcdbSubservice'] = relationship()

    individualservice_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbindividualservice.id"))
    individualservice: Mapped['KcdbIndividualService'] = relationship()

    quantity_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbquantity.id"))
    quantity: Mapped['KcdbQuantity'] = relationship()

    instrument_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbinstrument.id"))
    instrument: Mapped["KcdbInstrument"] = relationship()

    instrumentmethod_id: Mapped[Optional[int]] = \
        mapped_column(ForeignKey("kcdbinstrumentmethod.id"))
    instrumentmethod: Mapped["KcdbInstrumentMethod"] = relationship()

    parameters: Mapped[list['KcdbParameter']] = \
        relationship(back_populates='kcdbcmc')

    tags: Mapped[list['ClassifierTag']] = \
        relationship(secondary=kcdb_classifier_map, backref="kcdbcmcs")

    measurands: Mapped[list['MeasurandTaxon']] = \
        relationship(secondary=kcdb_measurand_map, backref="kcdbcmcs")
    # parents = relationship("Parent", secondary=association_table, back_populates="children")
    # parent_id = Column(String(50), ForeignKey("parent_table.id"))
    # parents = relationship("Parent", back_populates='discipline') # bidirectional relationship

    def __str__(self):
        return f'{self.kcdbCode}'


class KcdbParameter(Base):
    __tablename__ = "kcdbparameter"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(UnicodeText)
    value = Column(UnicodeText)
    kcdbcmc = relationship('KcdbCmc', back_populates='parameters')
    kcdbcmc_id = Column(Integer, ForeignKey('kcdbcmc.id'))

    def __str__(self):
        return f'name: {self.name} value: {self.value}'


class KcdbInstrument(Base):
    __tablename__ = "kcdbinstrument"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbInstrumentMethod(Base):
    __tablename__ = "kcdbinstrumentmethod"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbQuantity(Base):
    __tablename__ = "kcdbquantity"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbArea(Base):
    __tablename__ = "kcdbarea"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbBranch(Base):
    __tablename__ = "kcdbbranch"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'

    
class KcdbService(Base):
    __tablename__ = "kcdbservice"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbSubservice(Base):
    __tablename__ = "kcdbsubservice"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'


class KcdbIndividualService(Base):
    __tablename__ = "kcdbindividualservice"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    value: Mapped[str] = mapped_column(UnicodeText)

    def __str__(self):
        return f'{self.value}'

# Deprecated


class KcdbServiceClass(Base):
    __tablename__ = "kcdbserviceclass"
    id = Column(String(50), primary_key=True)
    area_id = Column(String(10))
    area = Column(String(50))
    branch_id = Column(String(20))
    branch = Column(String(50))
    service = Column(String(200))
    subservice = Column(String(200))
    individualservice = Column(String(200))

