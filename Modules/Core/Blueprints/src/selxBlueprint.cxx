#ifndef Blueprint_cxx
#define Blueprint_cxx

#include "boost/graph/graphviz.hpp"

#include "selxBlueprint.h"

namespace selx {

  // Declared outside of the class body, so it is a free function
  std::ostream& operator<<(std::ostream& out, const Blueprint::ParameterMapType& val){
    for (auto const & mapPair : val)
    {
      out << mapPair.first << " : [ ";
      for (auto const & value : mapPair.second)
      {
        out << value << " ";
      }
      out << "]\\n";
    }
    return out;
  }

  template <class ParameterMapType>
  class parameterMaplabel_writer {

  public:
    parameterMaplabel_writer(ParameterMapType _parameterMap) : parameterMap(_parameterMap) {}
    template <class VertexOrEdge>
    void operator()(std::ostream& out, const VertexOrEdge& v) const {
      out << "[label=\"" << parameterMap[v] << "\"]";
    }
  private:
    ParameterMapType parameterMap;
  };

  template <class ParameterMapType>
  inline parameterMaplabel_writer<ParameterMapType>
    make_parameterMaplabel_writer(ParameterMapType n) {
    return parameterMaplabel_writer<ParameterMapType>(n);
  }

bool
Blueprint
::AddComponent(ComponentNameType name)
{
  this->Modified();

  // Returns true is addition was successful 
  return this->m_Graph.insert_vertex(name, { name, { {} } }).second;
}

bool
Blueprint
::AddComponent(ComponentNameType name, ParameterMapType parameterMap)
{
  this->Modified();

  // Returns true is addition was successful 
  return this->m_Graph.insert_vertex(name, { name, parameterMap }).second;
}

Blueprint::ParameterMapType
Blueprint
::GetComponent(ComponentNameType name)
{
  this->Modified();
  return this->m_Graph[name].parameterMap;
}

void
Blueprint
::SetComponent(ComponentNameType name, ParameterMapType parameterMap)
{
  this->Modified();
  this->m_Graph[name].parameterMap = parameterMap;
}

// TODO: See explanation in selxBlueprint.h
// void
// Blueprint
// ::DeleteComponent( const ComponentIndexType index )
// {
//   this->Modified();
//
//   clear_vertex( index, this->m_Graph );
//   remove_vertex( index, this->m_Graph );
// }

Blueprint::ComponentNamesType Blueprint::GetComponentNames(void){
  ComponentNamesType container;
  for (auto it = boost::vertices(this->m_Graph.graph()).first; it != boost::vertices(this->m_Graph.graph()).second; ++it){
    container.push_back(this->m_Graph.graph()[*it].name);
  }
  return container;
}

bool
Blueprint
::AddConnection(ComponentNameType upstream, ComponentNameType downstream)
{
  this->Modified();

  if( this->ConnectionExists( upstream, downstream) ) {
    return false;
  }
  
  // Adds directed connection from upstream component to downstream component
  return boost::add_edge_by_label(upstream, downstream, this->m_Graph).second;
}

bool
Blueprint
::AddConnection(ComponentNameType upstream, ComponentNameType downstream, ParameterMapType parameterMap)
{
  this->Modified();

  if( !this->ConnectionExists( upstream, downstream ) ) {
    boost::add_edge_by_label(upstream, downstream,  { parameterMap }, this->m_Graph);
    return true;
  }

  // If the connection does not exist don't do anything because previous settings 
  // will be overwritten.  If the user do want to overwrite current settings, 
  // she should use SetConnection() instead where the intent is explicit.  
  return false;
}

Blueprint::ParameterMapType
Blueprint
::GetConnection( ComponentNameType upstream, ComponentNameType downstream )
{
  this->Modified();

  return this->m_Graph[ this->GetConnectionIndex( upstream, downstream ) ].parameterMap;
}

bool
Blueprint
::SetConnection(ComponentNameType upstream, ComponentNameType downstream, ParameterMapType parameterMap)
{
  this->Modified();

  if( !this->ConnectionExists( upstream, downstream ) ) {
    return this->AddConnection( upstream, downstream, parameterMap );
  } else {
    this->m_Graph[ this->GetConnectionIndex( upstream, downstream ) ].parameterMap = parameterMap;
    return true;
  }
}

bool
Blueprint
::DeleteConnection(ComponentNameType upstream, ComponentNameType downstream)
{
  this->Modified();

  if( this->ConnectionExists( upstream, downstream ) ) {
    boost::remove_edge_by_label(upstream, downstream, this->m_Graph);
  }
  
  return !this->ConnectionExists( upstream, downstream );
}

bool
Blueprint
::ConnectionExists( ComponentNameType upstream, ComponentNameType downstream )
{
  return boost::edge_by_label( upstream, downstream, this->m_Graph).second;
}

// TODO: can we really regard this as deprecated? Remove then.
/*
Blueprint::ConnectionIteratorPairType
Blueprint
::GetConnectionIterator(void) {
  return boost::edges(this->m_Graph);
}

Blueprint::OutputIteratorPairType
Blueprint
::GetOutputIterator(const ComponentNameType name) {
  return boost::out_edges(this->m_Graph.vertex(name), this->m_Graph);
}
*/
Blueprint::ComponentNamesType
Blueprint
::GetOutputNames(const ComponentNameType name) {
  ComponentNamesType container;
  OutputIteratorPairType outputIteratorPair = boost::out_edges(this->m_Graph.vertex(name), this->m_Graph);
  for (auto it = outputIteratorPair.first; it != outputIteratorPair.second; ++it){
    //boost::vertex()
    //boost::edge_by_label(upstream, downstream, this->m_Graph).first
    container.push_back(this->m_Graph.graph()[it->m_target].name);
  }

  return container;
}


Blueprint::ConnectionIndexType
Blueprint
::GetConnectionIndex( ComponentNameType upstream, ComponentNameType downstream )
{
  // This function is part of the internal API and should fail hard if we use it incorrectly
  if( !this->ConnectionExists( upstream, downstream ) ) {
    itkExceptionMacro( "Blueprint does not contain connection from component " << upstream << " to " << downstream );
  }
  
  return boost::edge_by_label(upstream, downstream, this->m_Graph).first;
}

void 
Blueprint
::WriteBlueprint( const std::string filename ) 
{
  std::ofstream dotfile( filename.c_str() );
  boost::write_graphviz(dotfile, this->m_Graph, make_parameterMaplabel_writer(boost::get(&ComponentPropertyType::parameterMap, this->m_Graph)), make_parameterMaplabel_writer(boost::get(&ConnectionPropertyType::parameterMap, this->m_Graph)));
}

} // namespace selx 

#endif // Blueprint_cxx
