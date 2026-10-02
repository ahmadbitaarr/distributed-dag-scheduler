package edu.vt.dag;

import java.util.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static edu.vt.dag.Model.*;

class ManifestValidatorTest {
    TaskSpec t(String name,List<String> parents){return new TaskSpec(name,"fixture_write",new Parameters(1L,null,null,null),parents,Map.of(),List.of("value"));}
    Manifest m(List<TaskSpec> tasks){return new Manifest(1,UUID.randomUUID(),tasks,Map.of("out",new OutputBinding("A","value")));}
    @Test void rootsAndDisconnectedGraphsAreValid(){assertDoesNotThrow(()->ManifestValidator.validate(m(List.of(t("A",List.of()),t("B",List.of())))));}
    @Test void rejectsCyclesUnknownSelfAndRepeatedParents(){
        for(var tasks:List.of(List.of(t("A",List.of("B")),t("B",List.of("A"))),List.of(t("A",List.of("missing"))),List.of(t("A",List.of("A"))),List.of(t("A",List.of()),t("B",List.of("A","A")))))
            assertThrows(ApiException.class,()->ManifestValidator.validate(m(tasks)));
    }
    @Test void taskAndEdgeLimitsAreExplicit(){
        var tasks=new ArrayList<TaskSpec>();for(int i=0;i<129;i++)tasks.add(t("T"+i,List.of()));
        assertEquals(413,assertThrows(ApiException.class,()->ManifestValidator.validate(m(tasks))).status);
        tasks.clear();var parents=new ArrayList<String>();for(int i=0;i<34;i++){tasks.add(t("T"+i,List.copyOf(parents)));parents.add("T"+i);}
        assertEquals(413,assertThrows(ApiException.class,()->ManifestValidator.validate(m(tasks))).status);
    }
    @Test void immutableSemanticNormalization(){
        var a=t("A",List.of());var b=t("B",List.of());UUID id=UUID.randomUUID();var outputs=Map.of("out",new OutputBinding("A","value"));
        var first=new Manifest(1,id,List.of(a,b),outputs);var second=new Manifest(1,id,List.of(b,a),outputs);
        assertEquals(first,second);assertThrows(UnsupportedOperationException.class,()->first.tasks().clear());
    }
    @Test void artifactNamesAndLimits(){
        String input="inputs/"+UUID.randomUUID()+"/clip.mp4";
        assertTrue(ManifestValidator.validKey(input));assertFalse(ManifestValidator.validKey(input+"/../x"));
        assertEquals(413,assertThrows(ApiException.class,()->ManifestValidator.artifact(new Artifact(input,33554433L,"0".repeat(64),"video/mp4"))).status);
    }
    @Test void bindingMustNameDeclaredParentAndOutput(){
        var source=t("A",List.of());
        for(var binding:List.of(new Binding(null,"A","missing"),new Binding(null,"X","value"))){
            var child=new TaskSpec("B","fixture_add",new Parameters(null,2L,null,null),List.of("A"),Map.of("value",binding),List.of("value"));
            assertThrows(ApiException.class,()->ManifestValidator.validate(m(List.of(source,child))));
        }
    }
}
