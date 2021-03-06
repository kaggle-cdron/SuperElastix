/*=========================================================================
 *
 *  Copyright Leiden University Medical Center, Erasmus University Medical
 *  Center and contributors
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0.txt
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *=========================================================================*/

#include "selxItkVectorImageSourceComponent.h"
#include "selxCheckTemplateProperties.h"

namespace selx
{
template< int Dimensionality, class TPixel >
ItkVectorImageSourceComponent< Dimensionality, TPixel >
::ItkVectorImageSourceComponent( const std::string & name, LoggerImpl & logger ) : Superclass( name, logger ), m_VectorImage( nullptr )
{
}


template< int Dimensionality, class TPixel >
ItkVectorImageSourceComponent< Dimensionality, TPixel >
::~ItkVectorImageSourceComponent()
{
}


template< int Dimensionality, class TPixel >
typename ItkVectorImageSourceComponent< Dimensionality, TPixel >::ItkVectorImageType::Pointer
ItkVectorImageSourceComponent< Dimensionality, TPixel >
::GetItkVectorImage()
{
  if( this->m_VectorImage == nullptr )
  {
    throw std::runtime_error( "SourceComponent needs to be initialized by SetMiniPipelineInput()" );
  }
  return this->m_VectorImage;
}


template< int Dimensionality, class TPixel >
typename ItkVectorImageSourceComponent< Dimensionality, TPixel >::ItkImageDomainPointer
ItkVectorImageSourceComponent< Dimensionality, TPixel >
::GetItkImageDomainFixed()
{
  if( this->m_VectorImage == nullptr )
  {
    throw std::runtime_error( "SourceComponent needs to be initialized by SetMiniPipelineInput()" );
  }
  return m_VectorImage.GetPointer();
}


template< int Dimensionality, class TPixel >
void
ItkVectorImageSourceComponent< Dimensionality, TPixel >
::SetMiniPipelineInput( itk::DataObject::Pointer object )
{
  this->m_VectorImage = dynamic_cast< ItkVectorImageType * >( object.GetPointer() );
  if( this->m_VectorImage == nullptr )
  {
    throw std::runtime_error( "DataObject passed by the NetworkBuilder is not of the right VectorImageType or not at all an VectorImageType" );
  }
  return;
}


template< int Dimensionality, class TPixel>
typename AnyFileReader::Pointer
ItkVectorImageSourceComponent< Dimensionality, TPixel >::GetInputFileReader()
{
  // Instanstiate an image file reader, decorated such that it can be implicitly cast to an AnyFileReaderType
  return DecoratedReaderType::New().GetPointer();
}


template< int Dimensionality, class TPixel >
bool
ItkVectorImageSourceComponent< Dimensionality, TPixel >
::MeetsCriterion( const ComponentBase::CriterionType & criterion )
{
  bool hasUndefinedCriteria( false );
  bool meetsCriteria( false );
  auto status = CheckTemplateProperties( this->TemplateProperties(), criterion );
  if( status == CriterionStatus::Satisfied )
  {
    return true;
  }
  else if( status == CriterionStatus::Failed )
  {
    return false;
  } // else: CriterionStatus::Unknown

  return meetsCriteria;
}

} //end namespace selx
